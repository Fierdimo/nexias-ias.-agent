/**
 * Login con Google (nativo) que devuelve un `serverAuthCode` para que el
 * BACKEND obtenga el refresh token (offlineAccess) y pueda leer las hojas
 * incluso sin el usuario presente.
 *
 * Requiere un dev build de EAS (módulo nativo, no corre en Expo Go).
 * Configura los client IDs en frontend/.env:
 *   EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=...   (OAuth client tipo "Web")
 *   EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=...   (OAuth client iOS, en iPhone)
 */
import {
  GoogleSignin,
  statusCodes,
} from "@react-native-google-signin/google-signin";

const WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? "";
const IOS_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID;

let configured = false;

function ensureConfigured() {
  if (configured) return;
  GoogleSignin.configure({
    webClientId: WEB_CLIENT_ID,
    iosClientId: IOS_CLIENT_ID,
    offlineAccess: true, // => serverAuthCode para el backend
    scopes: ["https://www.googleapis.com/auth/drive.file"],
  });
  configured = true;
}

export const googleConfigured = WEB_CLIENT_ID.length > 0;

export class GoogleCancelled extends Error {}

/** Inicia sesión y devuelve el serverAuthCode. */
export async function signInForServerCode(): Promise<string> {
  ensureConfigured();
  try {
    await GoogleSignin.hasPlayServices({
      showPlayServicesUpdateDialog: true,
    });
    const res: any = await GoogleSignin.signIn();
    const code = res?.data?.serverAuthCode ?? res?.serverAuthCode;
    if (!code) {
      throw new Error(
        "Google no devolvió serverAuthCode. Revisa webClientId y offlineAccess."
      );
    }
    return code as string;
  } catch (e: any) {
    if (
      e?.code === statusCodes.SIGN_IN_CANCELLED ||
      e?.code === statusCodes.IN_PROGRESS
    ) {
      throw new GoogleCancelled("Cancelado");
    }
    throw e;
  }
}
