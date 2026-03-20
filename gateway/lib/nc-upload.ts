import * as fs from 'fs';
import * as path from 'path';
import { randomBytes } from 'crypto';

/**
 * Client pour l'upload WebDAV et le partage de fichiers vers Nextcloud Talk
 * Documentation: https://docs.nextcloud.com/server/latest/developer_manual/client_apis/WebDAV/
 */

const NC_BASE_URL = process.env.NC_TALK_BASE_URL?.replace(/\/$/, '') || '';
const NC_BOT_USERNAME = process.env.NC_BOT_USERNAME || '';
const NC_BOT_PASSWORD = process.env.NC_BOT_PASSWORD || '';

// Dossier distant où stocker les screenshots
const REMOTE_SCREENSHOTS_DIR = '/Talk/bot-screenshots';

// Mapping des extensions vers les types MIME
const MIME_TYPES: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
};

/**
 * Détecte le type MIME à partir de l'extension du fichier
 */
function getMimeType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  return MIME_TYPES[ext] || 'application/octet-stream';
}

/**
 * Vérifie si la configuration WebDAV est disponible
 */
export function isWebDAVConfigured(): boolean {
  return !!(NC_BASE_URL && NC_BOT_USERNAME && NC_BOT_PASSWORD);
}

/**
 * Upload un fichier vers Nextcloud via WebDAV
 * 
 * @param localFilePath - Chemin local du fichier à uploader
 * @param remoteFileName - Nom du fichier sur Nextcloud (optionnel, utilise le nom local par défaut)
 * @returns Chemin distant du fichier uploadé ou erreur
 */
export async function uploadFileViaWebDAV(
  localFilePath: string,
  remoteFileName?: string
): Promise<{ success: true; remotePath: string } | { success: false; error: string }> {
  if (!isWebDAVConfigured()) {
    return { success: false, error: 'Configuration WebDAV manquante (NC_BOT_USERNAME ou NC_BOT_PASSWORD)' };
  }

  try {
    // Vérifier que le fichier existe
    if (!fs.existsSync(localFilePath)) {
      return { success: false, error: `Fichier non trouvé: ${localFilePath}` };
    }

    // Générer le nom de fichier distant
    const fileName = remoteFileName || path.basename(localFilePath);
    const remotePath = `${REMOTE_SCREENSHOTS_DIR}/${fileName}`;

    // Lire le fichier
    const fileContent = fs.readFileSync(localFilePath);

    // URL WebDAV
    const webdavUrl = `${NC_BASE_URL}/remote.php/dav/files/${NC_BOT_USERNAME}${remotePath}`;

    console.info(`[NC-Upload] Upload WebDAV: ${webdavUrl}`);

    // Upload via WebDAV PUT
    const response = await fetch(webdavUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': getMimeType(localFilePath),
        'Authorization': 'Basic ' + Buffer.from(`${NC_BOT_USERNAME}:${NC_BOT_PASSWORD}`).toString('base64'),
      },
      body: fileContent,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[NC-Upload] Erreur WebDAV ${response.status}:`, errorText);
      return { success: false, error: `Erreur WebDAV ${response.status}: ${errorText}` };
    }

    console.info(`[NC-Upload] Fichier uploadé avec succès: ${remotePath}`);
    return { success: true, remotePath };

  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[NC-Upload] Exception:', errorMsg);
    return { success: false, error: errorMsg };
  }
}

/**
 * Partage un fichier dans une conversation Nextcloud Talk
 * 
 * @param filePath - Chemin du fichier dans Nextcloud (ex: /Talk/bot-screenshots/screen.png)
 * @param conversationToken - Token de la conversation
 * @returns Succès ou erreur
 */
export async function shareFileToConversation(
  filePath: string,
  conversationToken: string
): Promise<{ success: true } | { success: false; error: string }> {
  if (!isWebDAVConfigured()) {
    return { success: false, error: 'Configuration WebDAV manquante' };
  }

  try {
    // L'API de partage utilise le chemin relatif au dossier utilisateur
    // Le partage vers une conversation utilise shareType=10
    const shareUrl = `${NC_BASE_URL}/ocs/v2.php/apps/files_sharing/api/v1/shares`;

    const payload = {
      shareType: 10, // Partage vers une conversation Talk
      shareWith: conversationToken,
      path: filePath,
      referenceId: generateReferenceId(),
    };

    console.info(`[NC-Upload] Partage fichier: ${filePath} → conversation ${conversationToken}`);

    const response = await fetch(shareUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'OCS-APIRequest': 'true',
        'Authorization': 'Basic ' + Buffer.from(`${NC_BOT_USERNAME}:${NC_BOT_PASSWORD}`).toString('base64'),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[NC-Upload] Erreur partage ${response.status}:`, errorText);
      return { success: false, error: `Erreur partage ${response.status}: ${errorText}` };
    }

    const result = await response.json();
    console.info(`[NC-Upload] Fichier partagé avec succès:`, result);
    return { success: true };

  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[NC-Upload] Exception partage:', errorMsg);
    return { success: false, error: errorMsg };
  }
}

/**
 * Upload un screenshot et le partage dans une conversation
 * Fonction combinée pour simplifier l'usage
 * 
 * @param localFilePath - Chemin local du screenshot
 * @param conversationToken - Token de la conversation Talk
 * @returns Succès avec chemin distant ou erreur
 */
export async function uploadAndShareScreenshot(
  localFilePath: string,
  conversationToken: string
): Promise<{ success: true; remotePath: string } | { success: false; error: string }> {
  // 1. Upload via WebDAV
  const uploadResult = await uploadFileViaWebDAV(localFilePath);
  
  if (!uploadResult.success) {
    return uploadResult;
  }

  // 2. Partager dans la conversation
  const shareResult = await shareFileToConversation(uploadResult.remotePath, conversationToken);
  
  if (!shareResult.success) {
    return { success: false, error: shareResult.error };
  }

  // 3. Nettoyer le fichier local après succès
  try {
    fs.unlinkSync(localFilePath);
    console.info(`[NC-Upload] Fichier local supprimé: ${localFilePath}`);
  } catch (cleanupError) {
    // Non-bloquant: logger l'erreur mais ne pas échouer
    console.warn(`[NC-Upload] Impossible de supprimer le fichier local: ${localFilePath}`, cleanupError);
  }

  return { success: true, remotePath: uploadResult.remotePath };
}

/**
 * Génère un referenceId unique (SHA256 aléatoire)
 */
function generateReferenceId(): string {
  return randomBytes(32).toString('hex');
}

/**
 * Extrait les chemins de screenshots d'une réponse texte
 * Pattern: C:\tmp\myclawshots\screen_YYYYMMDD_HHMMSS.png
 */
export function extractScreenshotPaths(text: string): string[] {
  // Pattern Windows pour les screenshots my-claw (insensible à la casse pour la lettre de lecteur)
  const pattern = /[A-Za-z]:\\tmp\\myclawshots\\screen_\d{8}_\d{6}\.png/g;
  const matches = text.match(pattern);
  return matches || [];
}

/**
 * Vérifie si un texte contient un chemin de screenshot
 */
export function containsScreenshotPath(text: string): boolean {
  return extractScreenshotPaths(text).length > 0;
}
