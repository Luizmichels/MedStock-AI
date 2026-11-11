/**
 * Formato mínimo de e-mail: "algo@dominio.ext". A validação de verdade é a do
 * backend; esta só evita enviar o que está claramente errado.
 *
 * Cada parte do domínio exclui o ponto, então só há um jeito de casar o texto:
 * a regex roda em tempo linear, sem o retrocesso que a versão "\S+@\S+\.\S+"
 * permitia.
 */
const EMAIL = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/;

export function emailValido(texto: string): boolean {
  return EMAIL.test(texto);
}
