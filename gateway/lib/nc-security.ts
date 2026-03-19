import { createHmac, timingSafeEqual, randomBytes } from 'crypto';

/**
 * Sécurité pour Nextcloud Talk Bot (HMAC-SHA256)
 * Basé sur: https://nextcloud-talk.readthedocs.io/en/latest/bots/
 */

/**
 * Vérifie la signature HMAC-SHA256 envoyée par Nextcloud
 * Signature = HMAC(RANDOM + BODY, SECRET)
 * 
 * @param signature - Valeur de X-Nextcloud-Talk-Signature (hex)
 * @param random - Valeur de X-Nextcloud-Talk-Random
 * @param body - Corps brut de la requête (Buffer ou string)
 * @param secret - Secret partagé configuré dans Nextcloud
 */
export function verifyNCSignature(
  signature: string,
  random: string,
  body: string | Buffer,
  secret: string
): boolean {
  if (!signature || !random || !secret) return false;

  const hmac = createHmac('sha256', secret);
  hmac.update(random);
  hmac.update(body);
  const digest = hmac.digest('hex');

  try {
    return timingSafeEqual(
      Buffer.from(digest, 'hex'),
      Buffer.from(signature, 'hex')
    );
  } catch {
    return false;
  }
}

/**
 * Signe une requête sortante vers Nextcloud
 * Retourne le sel aléatoire et la signature calculée
 * 
 * IMPORTANT: La signature est calculée sur RANDOM + MESSAGE (pas sur le body JSON complet)
 * Voir: https://nextcloud-talk.readthedocs.io/en/latest/bots/
 * 
 * @param message - Texte du message à envoyer
 * @param secret - Secret partagé
 */
export function signNCRequest(message: string, secret: string) {
  const random = randomBytes(32).toString('hex');
  const hmac = createHmac('sha256', secret);
  hmac.update(random);
  hmac.update(message);  // Signature sur le message texte, pas le JSON
  const signature = hmac.digest('hex');

  return { random, signature };
}
