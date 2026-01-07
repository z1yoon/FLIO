"""
FLIO Database Models and Connections
Supabase client setup and database utilities
"""

import os
from typing import Optional
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Get or create Supabase client singleton
    Used across all services that need database access
    """
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        # For backend operations, use the secret key (new naming convention)
        supabase_key = os.getenv("SUPABASE_SECRET_KEY")
        
        # Debug logging
        logger.info(f"Initializing Supabase with URL: {supabase_url}")
        logger.info(f"Using secret key: {supabase_key[:20]}..." if supabase_key else "No key found")
        
        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable not found")
        if not supabase_key:
            raise ValueError("SUPABASE_SECRET_KEY environment variable not found")
        
        # Remove quotes if present
        supabase_url = supabase_url.strip('"').strip("'")
        supabase_key = supabase_key.strip('"').strip("'")
        
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    return _supabase_client