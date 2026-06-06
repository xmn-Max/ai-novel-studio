import { useMemo } from 'react';

interface Character {
  id?: string;
  name: string;
  role?: string;
}

export function useProtagonistValidation(characters: Character[]): {
  protagonistName: string;
  isUnique: boolean;
  exists: boolean;
  message: string;
} {
  return useMemo(() => {
    const protagonists = characters.filter(c => c.role === 'protagonist');
    if (protagonists.length === 0) {
      return { protagonistName: '', isUnique: false, exists: false, message: '未找到主角' };
    }
    if (protagonists.length === 1) {
      return {
        protagonistName: protagonists[0].name,
        isUnique: true,
        exists: true,
        message: '验证通过',
      };
    }
    return {
      protagonistName: protagonists.map(c => c.name).join(', '),
      isUnique: false,
      exists: true,
      message: '警告：存在多个主角',
    };
  }, [characters]);
}
