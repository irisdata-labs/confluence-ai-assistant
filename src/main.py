from src.dispatcher import handle_request
from src.confluence_client import close_client
import atexit
import signal
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def cleanup():
    """Cleanup function to close MCP client"""
    print("\n🔒 Cleaning up...")
    close_client()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n👋 Goodbye!")
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Register cleanup functions
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🤖 Hybrid Assistant running. Type 'quit' to exit.")
    print("Available commands: search, create page, get page, etc.")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break
                
            if not user_input:
                continue
                
            print("🤔 Processing...")
            result = handle_request(user_input)
            print("🤖 Assistant:", result)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            print("Let's try again...")
    
    cleanup()
    print("👋 Goodbye!")