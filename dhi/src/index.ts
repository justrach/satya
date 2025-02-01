import { DhiType } from './core';
export { DhiType } from './core';
export type { ValidationResult, ValidationError } from './core';

// Factory function to create new DhiType instances
export async function createType<T>(): Promise<DhiType<T>> {
    return DhiType.create<T>();
} 