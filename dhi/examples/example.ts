import { createType } from '../src';

async function main() {
    try {
        // Create base types
        const string = await createType<string>();
        const number = await createType<number>();
        const boolean = await createType<boolean>();

        // Create a user schema
        const UserSchema = (await createType<any>()).object({
            name: string.string(),
            age: number.number(),
            isAdmin: boolean.boolean(),
            tags: (await createType<string[]>()).array(string.string())
        });

        // Valid data
        const validUser = {
            name: "John Doe",
            age: 30,
            isAdmin: true,
            tags: ["user", "premium"]
        };

        // Invalid data
        const invalidUser = {
            name: 123,  // should be string
            age: "30",  // should be number
            isAdmin: "yes",  // should be boolean
            tags: "tags"  // should be array
        };

        // Test validation
        console.log("\nValidating valid user:");
        console.log(UserSchema.validate(validUser));

        console.log("\nValidating invalid user:");
        console.log(UserSchema.validate(invalidUser));
    } catch (error) {
        console.error("Error:", error);
    }
}

// Run with Bun
main(); 