/**
 * 세션 ID 관리 유틸리티
 * 비로그인 사용자를 위한 고유 세션 ID 생성 및 관리
 */

const SESSION_KEY = 'modify_session_id';

/**
 * UUID v4 생성
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * 세션 ID 가져오기 (없으면 생성)
 */
export function getOrCreateSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_KEY);

  if (!sessionId) {
    sessionId = generateUUID();
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  return sessionId;
}

/**
 * 세션 ID 초기화 (로그아웃 시 사용)
 */
export function clearSessionId(): void {
  localStorage.removeItem(SESSION_KEY);
}

/**
 * 현재 세션 ID 조회 (생성하지 않음)
 */
export function getSessionId(): string | null {
  return localStorage.getItem(SESSION_KEY);
}
