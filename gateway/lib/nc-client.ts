import { signNCRequest } from './nc-security';

/**
 * Client pour l'API OCS Spreed (Nextcloud Talk)
 * Documentation: https://nextcloud-talk.readthedocs.io/en/latest/bots/
 */

const NC_BASE_URL = process.env.NC_TALK_BASE_URL?.replace(/\/$/, '') || '';
const NC_SECRET = process.env.NC_TALK_BOT_SECRET || '';

/**
 * Envoie un message dans une conversation Talk
 * 
 * @param conversationToken - Token de la conversation (from webhook target.id)
 * @param message - Texte du message
 * @param replyTo - ID du message auquel répondre (optionnel)
 */
export async function sendNCMessage(conversationToken: string, message: string, replyTo?: number) {
  if (!NC_BASE_URL || !NC_SECRET) {
    throw new Error('Configuration Nextcloud Talk Bot manquante (NC_TALK_BASE_URL ou NC_TALK_BOT_SECRET)');
  }

  const payload = { message, replyTo };
  const body = JSON.stringify(payload);
  
  // IMPORTANT: La signature est calculée sur le MESSAGE (pas sur le body JSON)
  // Voir: https://nextcloud-talk.readthedocs.io/en/latest/bots/
  const { random, signature } = signNCRequest(message, NC_SECRET);

  const url = `${NC_BASE_URL}/ocs/v2.php/apps/spreed/api/v1/bot/${conversationToken}/message`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'OCS-APIRequest': 'true',
      'X-Nextcloud-Talk-Bot-Random': random,
      'X-Nextcloud-Talk-Bot-Signature': signature,
    },
    body,
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error(`[NC-Client] Error sending message: ${response.status}`, errorText);
    throw new Error(`Nextcloud API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Ajoute une réaction emoji à un message
 * 
 * @param conversationToken - Token de la conversation (from webhook target.id)
 * @param messageId - ID du message auquel réagir
 * @param reaction - Emoji de réaction
 */
export async function addNCReaction(conversationToken: string, messageId: number, reaction: string) {
  if (!NC_BASE_URL || !NC_SECRET) {
    console.warn('[NC-Client] addNCReaction: Configuration manquante, opération ignorée');
    return;
  }

  const payload = { reaction };
  const body = JSON.stringify(payload);
  
  // IMPORTANT: La signature est calculée sur la REACTION (pas sur le body JSON)
  const { random, signature } = signNCRequest(reaction, NC_SECRET);

  const url = `${NC_BASE_URL}/ocs/v2.php/apps/spreed/api/v1/bot/${conversationToken}/reaction/${messageId}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'OCS-APIRequest': 'true',
      'X-Nextcloud-Talk-Bot-Random': random,
      'X-Nextcloud-Talk-Bot-Signature': signature,
    },
    body,
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error(`[NC-Client] Error adding reaction: ${response.status}`, errorText);
    throw new Error(`Nextcloud API error: ${response.status}`);
  }

  return response.json();
}
