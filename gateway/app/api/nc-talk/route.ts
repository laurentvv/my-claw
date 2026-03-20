import { NextRequest, NextResponse } from "next/server";
import { verifyNCSignature } from "@/lib/nc-security";
import { getOrCreateConversation, addMessage, getHistory } from "@/lib/memory";
import { runAgent } from "@/lib/agent-client";
import { sendNCMessage } from "@/lib/nc-client";
import {
  extractScreenshotPaths,
  uploadAndShareScreenshot,
  isWebDAVConfigured
} from "@/lib/nc-upload";

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
    // model: undefined → utilise DEFAULT_MODEL configuré dans agent/.env
    const model = undefined;
    // Valeur stockée en base: "main" indique que le modèle par défaut du système est utilisé
    const dbModel = "main";

    // Créer ou récupérer la conversation dans Prisma
    const conversation = await getOrCreateConversation(channel, conversationToken, dbModel);

    // Sauvegarder le message utilisateur
    await addMessage(conversation.id, "user", messageText, dbModel);

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
        await addMessage(conversation.id, "assistant", response, dbModel);
        
        // Détecter les screenshots dans la réponse
        const screenshotPaths = extractScreenshotPaths(response);
        let finalMessage = response;
        
        // Si des screenshots sont détectés et WebDAV configuré, les uploader et partager
        if (screenshotPaths.length > 0 && isWebDAVConfigured()) {
          console.info(`[NC-Webhook] ${screenshotPaths.length} screenshot(s) détecté(s), upload en cours...`);
          
          for (const screenshotPath of screenshotPaths) {
            const uploadResult = await uploadAndShareScreenshot(screenshotPath, conversationToken);
            
            if (uploadResult.success) {
              console.info(`[NC-Webhook] Screenshot uploadé et partagé: ${uploadResult.remotePath}`);
              // Nettoyer le chemin local du message final (replaceAll pour toutes les occurrences)
              finalMessage = finalMessage.replaceAll(screenshotPath, '').trim();
            } else {
              console.error(`[NC-Webhook] Erreur upload screenshot: ${uploadResult.error}`);
              // Garder le chemin dans le message si l'upload échoue
            }
          }
          
          // Nettoyer les lignes vides multiples et les espaces superflus
          finalMessage = finalMessage
            .replace(/\n{3,}/g, '\n\n')  // Max 2 sauts de ligne consécutifs
            .trim();
          
          // Si le message est vide après nettoyage, mettre un message par défaut
          if (!finalMessage) {
            finalMessage = "📸 Capture d'écran affichée ci-dessus.";
          }
        }
        
        // Envoyer le message à Nextcloud (OCS API) avec retry automatique
        // On peut répondre en citant le message d'origine (replyTo)
        await sendWithRetry(conversationToken, finalMessage, messageId);
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
