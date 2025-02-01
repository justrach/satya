import { createType } from '../src';

describe('Dhi Validation', () => {
  let UserSchema: Awaited<ReturnType<typeof createUserSchema>>;

  async function createUserSchema() {
    const string = await createType<string>();
    const number = await createType<number>();
    const boolean = await createType<boolean>();
    const stringArray = await createType<string[]>();

    return (await createType<any>()).object({
      id: number.number(),
      name: string.string(),
      email: string.string(),
      isActive: boolean.boolean(),
      tags: stringArray.array(string.string())
    });
  }

  beforeAll(async () => {
    UserSchema = await createUserSchema();
  });

  const validUser = {
    id: 1,
    name: "John Doe",
    email: "john@example.com",
    isActive: true,
    tags: ["user", "admin"]
  };

  const invalidUser = {
    id: "not-a-number",
    name: 123,
    email: "invalid-email",
    isActive: "true",
    tags: "not-an-array"
  };

  test('validates correct data', () => {
    const result = UserSchema.validate(validUser);
    expect(result.success).toBe(true);
    expect(result.data).toEqual(validUser);
  });

  test('fails on invalid data', () => {
    const result = UserSchema.validate(invalidUser);
    expect(result.success).toBe(false);
    expect(result.errors).toBeDefined();
    expect(result.errors?.length).toBeGreaterThan(0);
  });
}); 