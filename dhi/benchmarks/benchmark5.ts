import { z } from 'zod';
import { dhi } from '../src';

async function runBenchmark() {
    // Create complex nested schemas with new types
    const DhiAddressSchema = await dhi.object({
        street: await dhi.string(),
        city: await dhi.string(),
        country: await dhi.string(),
        zipCode: await dhi.string(),
        coordinates: await dhi.object({
            lat: await dhi.number(),
            lng: await dhi.number()
        })
    });

    const DhiContactSchema = await dhi.object({
        email: await dhi.string(),
        phone: await dhi.string(),
        address: DhiAddressSchema,
        lastContact: await dhi.date(),
        alternateEmails: await dhi.array(await dhi.string())
    });

    const DhiMetadataSchema = await dhi.object({
        createdAt: await dhi.date(),
        updatedAt: await dhi.date(),
        tags: await dhi.array(await dhi.string()),
        settings: await dhi.object({
            isPublic: await dhi.boolean(),
            notifications: await dhi.boolean(),
            preferences: await dhi.record<string, unknown>(await dhi.unknown())
        }),
        flags: await dhi.record<string, boolean>(await dhi.boolean())
    });

    const DhiUserSchema = await dhi.object({
        id: await dhi.string(),
        name: await dhi.string(),
        age: await dhi.number(),
        isAdmin: await dhi.boolean(),
        contact: DhiContactSchema,
        metadata: DhiMetadataSchema,
        friends: await dhi.array(await dhi.string()),
        status: await dhi.enum('active', 'inactive', 'banned'),
        loginCount: await dhi.bigint(),
        uniqueKey: await dhi.symbol(),
        lastLoginAttempt: await dhi.nullable(await dhi.date()),
        deletedAt: await dhi.optional(await dhi.date()),
        posts: await dhi.array(
            await dhi.object({
                id: await dhi.string(),
                title: await dhi.string(),
                content: await dhi.string(),
                likes: await dhi.number(),
                comments: await dhi.array(
                    await dhi.object({
                        id: await dhi.string(),
                        text: await dhi.string(),
                        author: await dhi.string()
                    })
                )
            })
        )
    });

    // Turn off debug mode
    DhiUserSchema.setDebug(false);

    // Create equivalent Zod schema
    const ZodUserSchema = z.object({
        id: z.string(),
        name: z.string(),
        age: z.number(),
        isAdmin: z.boolean(),
        contact: z.object({
            email: z.string(),
            phone: z.string(),
            address: z.object({
                street: z.string(),
                city: z.string(),
                country: z.string(),
                zipCode: z.string(),
                coordinates: z.object({
                    lat: z.number(),
                    lng: z.number()
                })
            }),
            lastContact: z.date(),
            alternateEmails: z.array(z.string())
        }),
        metadata: z.object({
            createdAt: z.date(),
            updatedAt: z.date(),
            tags: z.array(z.string()),
            settings: z.object({
                isPublic: z.boolean(),
                notifications: z.boolean(),
                preferences: z.record(z.unknown())
            }),
            flags: z.record(z.boolean())
        }),
        friends: z.array(z.string()),
        status: z.enum(['active', 'inactive', 'banned']),
        loginCount: z.bigint(),
        uniqueKey: z.symbol(),
        lastLoginAttempt: z.date().nullable(),
        deletedAt: z.date().optional(),
        posts: z.array(z.object({
            id: z.string(),
            title: z.string(),
            content: z.string(),
            likes: z.number(),
            comments: z.array(z.object({
                id: z.string(),
                text: z.string(),
                author: z.string()
            }))
        }))
    });

    // Generate complex test data
    const testData = Array.from({ length: 100_000 }, (_, i) => ({
        id: `user_${i}`,
        name: `User ${i}`,
        age: 20 + Math.floor(Math.random() * 50),
        isAdmin: Math.random() < 0.1,
        contact: {
            email: `user${i}@example.com`,
            phone: `+1${Math.floor(Math.random() * 10000000000)}`,
            address: {
                street: `${Math.floor(Math.random() * 1000)} Main St`,
                city: "New York",
                country: "USA",
                zipCode: "10001",
                coordinates: {
                    lat: Math.random() * 180 - 90,
                    lng: Math.random() * 360 - 180
                }
            },
            lastContact: new Date(),
            alternateEmails: [`alt${i}@example.com`]
        },
        metadata: {
            createdAt: new Date(),
            updatedAt: new Date(),
            tags: Array.from(
                { length: 1 + Math.floor(Math.random() * 4) },
                (_, j) => `tag${j}`
            ),
            settings: {
                isPublic: Math.random() < 0.5,
                notifications: Math.random() < 0.5,
                preferences: {
                    theme: Math.random() < 0.5 ? "light" : "dark",
                    language: "en",
                    timezone: "UTC"
                }
            },
            flags: {
                premium: Math.random() < 0.2,
                verified: Math.random() < 0.8
            }
        },
        friends: Array.from(
            { length: Math.floor(Math.random() * 10) },
            (_, j) => `friend_${j}`
        ),
        status: ['active', 'inactive', 'banned'][Math.floor(Math.random() * 3)] as any,
        loginCount: BigInt(Math.floor(Math.random() * 1000)),
        uniqueKey: Symbol('user'),
        lastLoginAttempt: Math.random() < 0.8 ? new Date() : null,
        deletedAt: Math.random() < 0.2 ? new Date() : undefined,
        posts: Array.from(
            { length: Math.floor(Math.random() * 5) },
            (_, j) => ({
                id: `post_${j}`,
                title: `Post ${j}`,
                content: `Content ${j}`,
                likes: Math.floor(Math.random() * 100),
                comments: Array.from(
                    { length: Math.floor(Math.random() * 3) },
                    (_, k) => ({
                        id: `comment_${k}`,
                        text: `Comment ${k}`,
                        author: `author_${k}`
                    })
                )
            })
        )
    }));

    // Warm up
    for (let i = 0; i < 100; i++) {
        DhiUserSchema.validate(testData[i]);
        ZodUserSchema.safeParse(testData[i]);
    }

    console.log(`\nBenchmarking complex validations with new types (${testData.length.toLocaleString()} items):`);
    
    // DHI Benchmark
    const dhiStart = performance.now();
    const dhiResults = DhiUserSchema.validate_batch(testData);
    const dhiTime = performance.now() - dhiStart;
    
    // Zod Benchmark
    const zodStart = performance.now();
    const zodResults = testData.map(item => ZodUserSchema.safeParse(item));
    const zodTime = performance.now() - zodStart;

    console.log('\nResults:');
    console.log(`DHI: ${dhiTime.toFixed(2)}ms`);
    console.log(`Zod: ${zodTime.toFixed(2)}ms`);
    console.log(`\nValidations per second:`);
    console.log(`DHI: ${(testData.length / (dhiTime / 1000)).toFixed(0).toLocaleString()}`);
    console.log(`Zod: ${(testData.length / (zodTime / 1000)).toFixed(0).toLocaleString()}`);
}

runBenchmark().catch(console.error); 