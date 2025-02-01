import { DhiType } from './core';

// Factory function for backward compatibility
export async function createType<T>(): Promise<DhiType<T>> {
    return DhiType.create<T>();
}

// Create the dhi object with static methods
export const dhi = {
    // Primitives
    string: async () => (await DhiType.create<string>()).string(),
    number: async () => (await DhiType.create<number>()).number(),
    boolean: async () => (await DhiType.create<boolean>()).boolean(),
    date: async () => (await DhiType.create<Date>()).date(),
    bigint: async () => (await DhiType.create<bigint>()).bigint(),
    symbol: async () => (await DhiType.create<symbol>()).symbol(),

    // Empty types
    undefined: async () => (await DhiType.create<undefined>()).undefined(),
    null: async () => (await DhiType.create<null>()).null(),
    void: async () => (await DhiType.create<void>()).void(),

    // Catch-all types
    any: async () => (await DhiType.create<any>()).any(),
    unknown: async () => (await DhiType.create<unknown>()).unknown(),

    // Never type
    never: async () => (await DhiType.create<never>()).never(),

    // Complex types
    array: async <T>(schema: DhiType<T>) => (await DhiType.create<T[]>()).array(schema),
    object: async <T extends Record<string, any>>(shape: { [K in keyof T]: DhiType<T[K]> }) => 
        (await DhiType.create<T>()).object(shape),
    record: async <K extends string, V>(valueType: DhiType<V>) => 
        (await DhiType.create<Record<K, V>>()).record(valueType),

    // Enum type
    enum: async <T extends [string, ...string[]]>(...values: T) => {
        const schema = await DhiType.create<T[number]>();
        return schema.setTypeString(`enum:${values.join(',')}`);
    },

    // Helper to create custom types
    create: DhiType.create,

    // Utilities
    optional: async <T>(schema: DhiType<T>) => schema.optional(),
    nullable: async <T>(schema: DhiType<T>) => schema.nullable(),
};

// Type definitions for better DX
export type {
    DhiType,
    ValidationResult,
    ValidationError
} from './core';

// Example usage:
/*
const UserSchema = await dhi.object({
    name: await dhi.string(),
    age: await dhi.number(),
    isAdmin: await dhi.boolean(),
    tags: await dhi.array(await dhi.string())
});

// Validate
const result = UserSchema.validate({
    name: "John",
    age: 30,
    isAdmin: true,
    tags: ["admin", "user"]
});
*/ 