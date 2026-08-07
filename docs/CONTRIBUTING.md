# Contributing

Thanks for your interest in contributing to Hydra Downloader.

## Getting started

1. Fork the repository and clone it.
2. Set up the development environment (see [DEVELOPER.md](DEVELOPER.md)).
3. Create a feature branch: `git checkout -b feature/your-feature`.

## Code of conduct

Be respectful, constructive, and inclusive. No harassment of any kind.

## Development workflow

- Keep changes focused and small.
- Follow the existing layer/clean-architecture conventions.
- Add unit tests for new services and components.
- Run the build and tests before submitting.

## Commit messages

Use clear, conventional commit messages:

```
feat: add audio-only download option
fix: handle playlist detection edge case
docs: update architecture diagram
```

## Pull requests

- Target the `main` branch.
- Describe the change and reference any related issues.
- Ensure the app compiles and tests pass.

## Adding a new backend endpoint

1. Create a Pydantic schema in `backend/app/models/`.
2. Implement the business logic in `backend/app/services/`.
3. Add a thin route in `backend/app/api/routes/`.
4. Register the router in `backend/app/main.py`.
5. Add tests in `backend/tests/`.
