# Coding Guidelines & Principles

## Table of Contents
1. [SOLID Principles](#solid-principles)
2. [Code Organization](#code-organization)
3. [Naming Conventions](#naming-conventions)
4. [Type Safety](#type-safety)
5. [Error Handling](#error-handling)
6. [Documentation](#documentation)
7. [Testing](#testing)
8. [Performance](#performance)

## SOLID Principles

### Single Responsibility Principle (SRP)
- Each class/function should have one reason to change
- Services should handle one domain (e.g., `AIService` for AI, `FileService` for files)
- Routers should only handle HTTP request/response logic

### Open/Closed Principle (OCP)
- Open for extension, closed for modification
- Use interfaces/abstract classes for extensibility
- Example: `AIProvider` interface allows adding new providers without modifying existing code

### Liskov Substitution Principle (LSP)
- Subtypes must be substitutable for their base types
- All `AIProvider` implementations must work interchangeably

### Interface Segregation Principle (ISP)
- Clients shouldn't depend on interfaces they don't use
- Keep interfaces focused and small (e.g., `IAIService`, `IFileService`)

### Dependency Inversion Principle (DIP)
- Depend on abstractions, not concretions
- Use dependency injection for services
- Example: `AIService` depends on `AIProvider` interface, not concrete implementations

## Code Organization

### Backend Structure
```
backend/app/
├── core/           # Core configuration and utilities
├── domain/         # Domain entities and value objects
├── models/         # Pydantic models for API
├── routers/        # API route handlers (thin layer)
├── services/       # Business logic (thick layer)
├── repositories/   # Data access layer
└── utils/          # Utility functions
```

### Frontend Structure
```
frontend/src/
├── components/     # React components (presentation)
├── hooks/          # Custom React hooks (state logic)
├── services/       # API clients and external services
├── types/          # TypeScript type definitions
└── utils/          # Utility functions
```

### File Naming
- **Python**: `snake_case.py` (e.g., `document_service.py`)
- **TypeScript**: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- **Constants**: `UPPER_SNAKE_CASE`

## Naming Conventions

### Python
- **Classes**: `PascalCase` (e.g., `DocumentService`)
- **Functions/Methods**: `snake_case` (e.g., `get_document`)
- **Variables**: `snake_case` (e.g., `document_id`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`)
- **Private**: `_leading_underscore` (e.g., `_internal_method`)

### TypeScript
- **Components**: `PascalCase` (e.g., `DocumentViewer`)
- **Functions/Variables**: `camelCase` (e.g., `getDocument`)
- **Types/Interfaces**: `PascalCase` (e.g., `Document`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `API_URL`)

## Type Safety

### Python
- Use type hints for all function parameters and return types
- Use `Optional[T]` for nullable types
- Use `List[T]`, `Dict[K, V]` for collections
- Example:
```python
def get_document(doc_id: str) -> Optional[DocumentMetadata]:
    ...
```

### TypeScript
- Avoid `any` type - use `unknown` if type is truly unknown
- Use interfaces for object shapes
- Use union types for multiple possibilities
- Example:
```typescript
function getDocument(id: string): Promise<Document | null> {
    ...
}
```

## Error Handling

### Python
- Use specific exception types
- Don't catch generic `Exception` unless necessary
- Provide meaningful error messages
- Use HTTPException for API errors
- Example:
```python
if not document:
    raise HTTPException(status_code=404, detail="Document not found")
```

### TypeScript
- Use try-catch for async operations
- Provide user-friendly error messages
- Log errors for debugging
- Example:
```typescript
try {
    const doc = await api.getDocument(id);
} catch (error) {
    console.error('Failed to fetch document:', error);
    throw new Error('Failed to load document');
}
```

## Documentation

### Python Docstrings
- Use Google-style docstrings
- Document parameters, return values, and exceptions
- Example:
```python
def process_document(doc_id: str, file_path: Path) -> None:
    """
    Process a document with AI services.
    
    Args:
        doc_id: Unique document identifier
        file_path: Path to the document file
        
    Raises:
        ValueError: If document file is not found
        HTTPException: If AI processing fails
    """
```

### TypeScript JSDoc
- Use JSDoc comments for complex functions
- Document parameters and return types
- Example:
```typescript
/**
 * Fetches a document by ID from the API
 * @param id - Document identifier
 * @returns Promise resolving to Document or null if not found
 */
async function getDocument(id: string): Promise<Document | null> {
    ...
}
```

## Testing

### Unit Tests
- Test one thing at a time
- Use descriptive test names
- Follow AAA pattern: Arrange, Act, Assert
- Mock external dependencies

### Integration Tests
- Test complete workflows
- Use test databases/storage
- Clean up after tests

## Performance

### Backend
- Use async/await for I/O operations
- Batch database operations when possible
- Cache frequently accessed data
- Use connection pooling for databases

### Frontend
- Use React.memo for expensive components
- Lazy load components
- Debounce search inputs
- Optimize re-renders with useMemo/useCallback

## Code Quality

### DRY (Don't Repeat Yourself)
- Extract common logic into functions/utilities
- Reuse components
- Avoid code duplication

### KISS (Keep It Simple, Stupid)
- Prefer simple solutions over complex ones
- Avoid premature optimization
- Write readable code

### YAGNI (You Aren't Gonna Need It)
- Don't add functionality until needed
- Avoid over-engineering
- Focus on current requirements

## Best Practices

### Backend
1. **Dependency Injection**: Pass dependencies as parameters
2. **Configuration**: Use environment variables, not hardcoded values
3. **Logging**: Use proper logging levels (DEBUG, INFO, WARNING, ERROR)
4. **Validation**: Validate input at API boundaries
5. **Security**: Sanitize user input, use parameterized queries

### Frontend
1. **Component Composition**: Build complex UIs from simple components
2. **State Management**: Use appropriate state management (local state vs context)
3. **Performance**: Optimize bundle size, use code splitting
4. **Accessibility**: Use semantic HTML, ARIA labels
5. **Responsive Design**: Mobile-first approach

## Code Review Checklist

- [ ] Follows SOLID principles
- [ ] Has proper type hints/TypeScript types
- [ ] Includes error handling
- [ ] Has documentation/comments
- [ ] No hardcoded values
- [ ] Follows naming conventions
- [ ] No code duplication
- [ ] Tests included (if applicable)
- [ ] Performance considerations addressed

