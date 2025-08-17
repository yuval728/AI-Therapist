"""Setup script for Supabase database initialization."""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.database import get_supabase_client
from src.config import get_settings
from src.utils import log_therapy_event


async def setup_database():
    """Initialize Supabase database with schema and test connection."""
    print("🚀 Setting up Supabase database...")
    
    try:
        # Initialize client
        client = await get_supabase_client()
        print("✅ Supabase client initialized successfully")
        
        # Test basic operations
        await test_database_operations(client)
        
        print("🎉 Supabase setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Supabase setup failed: {str(e)}")
        return False


async def test_database_operations(client):
    """Test basic database operations."""
    print("\n🧪 Testing database operations...")
    
    # Test 1: Check if tables exist
    try:
        result = client.client.table("profiles").select("count", count="exact").limit(1).execute()
        print("✅ Profiles table accessible")
    except Exception as e:
        print(f"❌ Profiles table test failed: {str(e)}")
    
    try:
        result = client.client.table("memory_logs").select("count", count="exact").limit(1).execute()
        print("✅ Memory logs table accessible")
    except Exception as e:
        print(f"❌ Memory logs table test failed: {str(e)}")
    
    try:
        result = client.client.table("documents").select("count", count="exact").limit(1).execute()
        print("✅ Documents table accessible")
    except Exception as e:
        print(f"❌ Documents table test failed: {str(e)}")
    
    # Test 2: Test RPC function
    try:
        # Test with dummy data
        result = client.client.rpc("match_documents", {
            "user_id_param": "00000000-0000-0000-0000-000000000000",
            "query_embedding": [0.0] * 768,
            "match_threshold": 0.5,
            "match_count": 1
        }).execute()
        print("✅ Vector search function accessible")
    except Exception as e:
        print(f"❌ Vector search test failed: {str(e)}")


def check_environment():
    """Check if required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY", 
        "GOOGLE_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=your_value_here")
        return False
    
    print("✅ All required environment variables are set")
    return True


def print_schema_info():
    """Print information about the database schema."""
    print("\n📋 Database Schema Information:")
    print("=" * 50)
    
    tables = {
        "profiles": "User profiles linked to Supabase Auth",
        "therapy_sessions": "Therapy session tracking and metadata",
        "memory_logs": "Short-term conversation memory",
        "crisis_events": "Crisis detection and escalation tracking",
        "documents": "Long-term memory with vector embeddings",
        "security_events": "Security event logging",
        "performance_metrics": "Performance monitoring data"
    }
    
    for table, description in tables.items():
        print(f"  📊 {table:<20} - {description}")
    
    print("\n🔧 Key Features:")
    print("  • Row Level Security (RLS) enabled")
    print("  • Vector search with pgvector extension")
    print("  • Automatic timestamps and triggers")
    print("  • Performance indexes")
    print("  • Crisis escalation tracking")


async def main():
    """Main setup function."""
    print("🏥 AI Therapist - Supabase Database Setup")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Print schema info
    print_schema_info()
    
    # Setup database
    success = await setup_database()
    
    if success:
        print("\n🎯 Next Steps:")
        print("  1. Run the database migration: supabase db push")
        print("  2. Test the integration with: python -m pytest tests/test_refactored_integration.py")
        print("  3. Start your application")
        sys.exit(0)
    else:
        print("\n💡 Troubleshooting:")
        print("  1. Check your environment variables")
        print("  2. Verify Supabase project is running")
        print("  3. Ensure database schema is applied")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
