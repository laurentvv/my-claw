import { NextRequest, NextResponse } from "next/server";
import { verifyNCSignature } from "@/lib/nc-security";
import { getOrCreateConversation, addMessage, getHistory } from "@/lib/memory";
import { runAgent } from "@/lib/agent-client";
import { sendNCMessage } from "@/lib/nc-client";

/**
 * Webhook API pour Nextcloud Talk Bot
 * Reçoit les activités ActivityStreams 2.0
 */

/**
 * Envoie un message avec retry automatique
 * @param maxRetries - Nombre maximum de tentatives (défaut: 3)
 * @param baseDelayMs - Délai de base en ms, augmente exponentiellement (défaut: 1000ms)
 */
async function sendWithRetry(
  conversationToken: string,
  message: string,
  replyTo?: number,
  maxRetries = 3,
  baseDelayMs = 1000
): Promise<void> {
  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      await sendNCMessage(conversationToken, message, replyTo);
      return;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      console.warn(`[NC-Webhook] Tentative ${attempt + 1}/${maxRetries} échouée:`, lastError.message);
      
      if (attempt < maxRetries - 1) {
        // Backoff exponentiel: 1s, 2s, 4s...
        const delay = baseDelayMs * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError;
}

export async function POST(req: NextRequest) {
  try {
    const signature = req.headers.get("X-Nextcloud-Talk-Signature");
    const random = req.headers.get("X-Nextcloud-Talk-Random");
    const secret = process.env.NC_TALK_BOT_SECRET;

    if (!secret) {
      console.error("[NC-Webhook] NC_TALK_BOT_SECRET non configuré");
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }

    // Récupérer le corps brut pour la validation HMAC
    const rawBody = await req.text();

    // 1. Vérification de la signature
    if (!signature || !random || !verifyNCSignature(signature, random, rawBody, secret)) {
      console.warn("[NC-Webhook] Signature invalide");
      return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
    }

    // 2. Parser l'activité
    const activity = JSON.parse(rawBody);
    const type = activity.type;

    console.info(`[NC-Webhook] Activité reçue: ${type}`);

    // On ne traite que les nouveaux messages pour l'instant
    if (type !== "Create") {
      return NextResponse.json({ status: "ignored" });
    }

    const actor = activity.actor || {};
    const obj = activity.object || {};
    const target = activity.target || {};

    // Extraire les infos
    const conversationToken = target.id; // Token de la conversation Nextcloud
    const messageId = parseInt(obj.id);
    
    // Contenu Talk: est un JSON stringifié contenant "message" et "parameters"
    let messageText = "";
    try {
      const content = JSON.parse(obj.content || "{}");
      messageText = content.message || "";
    } catch {
      messageText = obj.content || "";
    }

    if (!messageText || !conversationToken) {
      return NextResponse.json({ status: "no_content" });
    }

    // 3. Orchestration my-claw
    // Utilisation du channel "nc-talk" et du token conversation comme channelId
    const channel = "nc-talk";
    const model = "main"; // Modèle par défaut pour Talk

    // Créer ou récupérer la conversation dans Prisma
    const conversation = await getOrCreateConversation(channel, conversationToken, model);

    // Sauvegarder le message utilisateur
    await addMessage(conversation.id, "user", messageText, model);

    // Récupérer l'historique (10 derniers messages pour le contexte)
    const history = await getHistory(conversation.id, 10);

    // Exécuter l'agent Python (Asynchrone : on répond 200 OK à NC, puis on envoie la réponse NC après)
    // Nextcloud attend une réponse 200 OK rapide au webhook.
    
    // On lance le traitement en arrière-plan (non-blocking pour le webhook)
    (async () => {
      try {
        console.info(`[NC-Webhook] Appel de l'agent pour: ${conversationToken}`);
        const response = await runAgent(messageText, history, model);
        
        // Sauvegarder la réponse assistant
        await addMessage(conversation.id, "assistant", response, model);
        
        // Envoyer le message à Nextcloud (OCS API) avec retry automatique
        // On peut répondre en citant le message d'origine (replyTo)
        await sendWithRetry(conversationToken, response, messageId);
        console.info(`[NC-Webhook] Réponse envoyée à Nextcloud pour: ${conversationToken}`);
      } catch (agentError) {
        console.error("[NC-Webhook] Erreur Agent:", agentError);
        try {
          await sendWithRetry(conversationToken, "Désolé, j'ai rencontré une erreur lors du traitement de votre message.", messageId);
        } catch (sendError) {
          console.error("[NC-Webhook] Impossible d'envoyer le message d'erreur:", sendError);
        }
      }
    })();

    // Répondre immédiatement à Nextcloud que le webhook est reçu
    return NextResponse.json({ status: "received" });

  } catch (error) {
    console.error("[NC-Webhook] Error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
