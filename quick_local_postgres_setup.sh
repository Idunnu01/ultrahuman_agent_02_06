#!/bin/bash
# Quick local PostgreSQL setup with pgvector for testing

echo "🚀 Quick Local PostgreSQL Setup"
echo "================================"

# Install PostgreSQL via Homebrew
echo "📦 Installing PostgreSQL..."
brew install postgresql
brew install pgvector

# Start PostgreSQL service
echo "🔄 Starting PostgreSQL..."
brew services start postgresql

# Create database
echo "🗃️ Creating database..."
createdb ultrahuman_semantic

# Create user (optional)
echo "👤 Setting up user..."
psql ultrahuman_semantic -c "CREATE USER ultrahuman_user WITH PASSWORD 'ultrahuman_pass';"
psql ultrahuman_semantic -c "GRANT ALL PRIVILEGES ON DATABASE ultrahuman_semantic TO ultrahuman_user;"

# Enable pgvector extension
echo "🧮 Installing pgvector extension..."
psql ultrahuman_semantic -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "✅ Local PostgreSQL setup complete!"
echo ""
echo "💡 Update your .env file with:"
echo "POSTGRES_HOST=localhost"
echo "POSTGRES_PORT=5432"
echo "POSTGRES_DATABASE=ultrahuman_semantic"
echo "POSTGRES_USER=ultrahuman_user"
echo "POSTGRES_PASSWORD=ultrahuman_pass"
echo "POSTGRES_SSLMODE=prefer"
echo ""
echo "Then run: python setup_railway_db.py"