"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  ApiError,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  setToken,
  usuarioLogado,
} from "@/lib/api";

export type Perfil = "usuario" | "admin" | "super_admin";

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  perfil: Perfil;
  empresaId: number | null;
}

interface AuthContextValue {
  usuario: Usuario | null;
  carregando: boolean;
  entrar: (email: string, senha: string) => Promise<Usuario>;
  sair: () => void;
  /** Atualiza nome/e-mail exibidos depois que o usuário edita o próprio perfil. */
  atualizarUsuario: (dados: Partial<Pick<Usuario, "nome" | "email">>) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Decodifica o payload de um JWT sem validar a assinatura (feito no backend). */
function lerPayload(token: string): Partial<Usuario> | null {
  try {
    const base = token.split(".")[1];
    const json = atob(base.replace(/-/g, "+").replace(/_/g, "/"));
    const p = JSON.parse(json) as { sub?: string; perfil?: Perfil; empresa_id?: number };
    return {
      id: p.sub ?? "",
      perfil: (p.perfil ?? "usuario") as Perfil,
      empresaId: p.empresa_id ?? null,
    };
  } catch {
    return null;
  }
}

function usuarioDoToken(token: string, email = ""): Usuario | null {
  const payload = lerPayload(token);
  if (!payload) return null;
  return {
    id: payload.id ?? "",
    nome: "",
    email,
    perfil: payload.perfil ?? "usuario",
    empresaId: payload.empresaId ?? null,
  };
}

/** Completa o usuário do token com nome e e-mail vindos de /usuarios/me. */
async function completarComPerfil(u: Usuario): Promise<Usuario> {
  const me = await usuarioLogado();
  return { ...u, nome: me.nome, email: me.email };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    const token = getToken();
    const doToken = token ? usuarioDoToken(token) : null;
    if (!doToken) {
      setCarregando(false);
      return;
    }
    // Valida a sessão: se o usuário do token não existe mais ou o token expirou,
    // a API responde 401/404 e a sessão é encerrada.
    completarComPerfil(doToken)
      .then(setUsuario)
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 404)) {
          apiLogout();
          setUsuario(null);
        } else {
          setUsuario(doToken); // API fora do ar: mantém a sessão com os dados do token
        }
      })
      .finally(() => setCarregando(false));
  }, []);

  const entrar = useCallback(async (email: string, senha: string) => {
    const { access_token } = await apiLogin(email, senha);
    const doToken = usuarioDoToken(access_token, email);
    if (!doToken) {
      setToken(null);
      throw new Error("Token inválido recebido do servidor.");
    }
    const u = await completarComPerfil(doToken).catch(() => doToken);
    setUsuario(u);
    return u;
  }, []);

  const sair = useCallback(() => {
    apiLogout();
    setUsuario(null);
  }, []);

  const atualizarUsuario = useCallback((dados: Partial<Pick<Usuario, "nome" | "email">>) => {
    setUsuario((atual) => (atual ? { ...atual, ...dados } : atual));
  }, []);

  return (
    <AuthContext.Provider value={{ usuario, carregando, entrar, sair, atualizarUsuario }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de <AuthProvider>.");
  return ctx;
}

/** Papel no vocabulário do design (super_admin -> super). */
export function papel(perfil: Perfil): "usuario" | "admin" | "super" {
  return perfil === "super_admin" ? "super" : perfil;
}
