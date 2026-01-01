# FLIO Coding Standards

## Core Principles
- Clean and simple code only
- No unnecessary code or features
- Consistent style across all files
- Minimal dependencies

## Code Style

### TypeScript/JavaScript
```typescript
// Use simple function declarations
function handleSubmit(data: FormData) {
  // Implementation
}

// Prefer const over let
const user = getUserData();

// Simple destructuring
const { name, email } = user;

// Clean async/await
async function fetchData() {
  const response = await api.get('/data');
  return response.data;
}
```

### React Components
```tsx
// Simple functional components
function UserProfile({ user }: { user: User }) {
  return (
    <div className="user-profile">
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  );
}

// Use simple state
const [loading, setLoading] = useState(false);
const [data, setData] = useState(null);
```

### File Structure
```
components/
  UserProfile.tsx
  Button.tsx
services/
  api.ts
  auth.ts
types/
  user.ts
  api.ts
```

## Rules
1. No comments unless absolutely necessary
2. No complex abstractions
3. No unnecessary imports
4. Simple variable names
5. One responsibility per function
6. Avoid nested ternary operators
7. Use early returns to avoid deep nesting

## What NOT to do
- Complex design patterns
- Over-engineering
- Unnecessary abstractions
- Verbose naming
- Deep component nesting
- Multiple responsibilities in one function