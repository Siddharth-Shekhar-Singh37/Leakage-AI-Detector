"""
Groq API Connection Test
Tests that the Groq API key is working correctly before
building the full AI report generator.
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Load API key from .env file
load_dotenv()

def test_connection():
    print("🔌 Testing Groq API connection...\n")

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("❌ API key not found!")
        print("   Make sure your .env file contains GROQ_API_KEY")
        return False

    print(f"✅ API key found: {api_key[:15]}...")

    # Create client
    client = Groq(api_key=api_key)

    # Send a simple test message
    print("📡 Sending test message to Groq...\n")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a water network analyst assistant. "
                    "In one sentence, describe what Minimum Night Flow means "
                    "in water distribution networks."
                )
            }
        ],
        max_tokens=200
    )

    print("✅ Groq responded successfully!")
    print(f"\n💬 Groq says:\n{response.choices[0].message.content}")
    return True


if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n🎉 API connection working perfectly!")
        print("   Ready to build the AI report generator!")
    else:
        print("\n❌ Connection failed. Check your API key.")