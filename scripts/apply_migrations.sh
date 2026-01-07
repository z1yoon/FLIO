#!/bin/bash
# Apply Supabase migrations via psql CLI
# Usage: ./scripts/apply_migrations.sh

set -e  # Exit on error

echo "🚀 Applying Supabase migrations via psql..."
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable is not set"
    echo ""
    echo "📋 To get your connection string:"
    echo "1. Go to: https://supabase.com/dashboard/project/oyzsfmreacsrbcxavjde"
    echo "2. Click 'Connect' button at the top"
    echo "3. Choose 'Direct connection' (supports IPv6)"
    echo "4. Copy the connection string"
    echo ""
    echo "Then run:"
    echo "export DATABASE_URL='postgresql://postgres:[YOUR-PASSWORD]@db.oyzsfmreacsrbcxavjde.supabase.co:5432/postgres'"
    echo "./scripts/apply_migrations.sh"
    exit 1
fi

echo "📊 Connection string: ${DATABASE_URL:0:30}..."
echo ""

# Apply migrations in order
migrations=(
    "supabase/migrations/004_questions_database.sql"
    "supabase/migrations/005_ai_backend_functions.sql"
    "supabase/migrations/006_user_answers_table.sql"
)

for migration in "${migrations[@]}"; do
    echo "📝 Applying: $migration"
    
    if psql "$DATABASE_URL" -f "$migration" > /tmp/migration_output.log 2>&1; then
        echo "✅ Success: $migration"
        # Show last few lines of output
        tail -3 /tmp/migration_output.log | grep -v "^$" || true
    else
        echo "❌ Failed: $migration"
        echo ""
        echo "Error output:"
        cat /tmp/migration_output.log
        exit 1
    fi
    echo ""
done

echo "🎉 All migrations applied successfully!"
echo ""
echo "Verify with:"
echo "psql \"\$DATABASE_URL\" -c 'SELECT COUNT(*) FROM questions;'"
echo "psql \"\$DATABASE_URL\" -c 'SELECT COUNT(*) FROM user_answers;'"
