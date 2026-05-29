#!/usr/bin/env python3
"""
Google Indexing API - Submit URLs for indexing
Requires a service account JSON key with Indexing API enabled.
The service account email must be added as Owner in Google Search Console.

Usage:
  python3 index_urls.py --credentials /path/to/service-account.json
"""

import argparse
import json
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/indexing"]

SITE_URL = "https://the-rogue-marketing.github.io"

# All blog post URLs to index
URLS = [
    # New May 2026 posts (OCR/Document Intelligence sprint)
    f"{SITE_URL}/best-invoice-receipt-automation-parsing-loyalty-points-pydantic-ai/",
    f"{SITE_URL}/best-resume-parser-pydantic-ai-gemini-fastapi/",
    f"{SITE_URL}/best-passport-parsing-api-pydantic-ai-gemini-fastapi/",
    f"{SITE_URL}/litellm-vs-pydantic-ai-production-pipelines/",
    f"{SITE_URL}/best-data-extraction-tools-2026/",
    f"{SITE_URL}/best-document-fraud-detection-software-2026/",
    f"{SITE_URL}/build-high-accuracy-automations-gemini-api/",
    f"{SITE_URL}/google-gemini-api-ocr-guide-pydantic-ai/",
    f"{SITE_URL}/ai-api-pricing-calculator/",
    f"{SITE_URL}/the-0-10-ai-models-guide-to-cheap-llm-apis/",
    f"{SITE_URL}/how-to-cut-your-ai-api-bill-by-90-percent/",
    f"{SITE_URL}/gemini-vs-gpt-vs-grok-vs-claude-api-cost-comparison/",
    f"{SITE_URL}/ai-api-free-tiers-compared/",
    f"{SITE_URL}/building-cheap-ai-chatbot-gemini-flash-lite/",
    f"{SITE_URL}/i-built-the-same-app-with-5-ai-apis-costs/",
    f"{SITE_URL}/grok-4-3-vs-gemini-3-1-pro-vs-claude-4-6/",
    f"{SITE_URL}/migrating-from-openai-to-gemini-step-by-step/",
    f"{SITE_URL}/build-ai-agent-under-10-dollars-deepseek-gemini/",
    f"{SITE_URL}/google-gemini-3-5-flash-worth-the-upgrade/",
    f"{SITE_URL}/openai-price-drop-breaking-down-gpt-5-5/",
    f"{SITE_URL}/deepseek-vs-major-ai-apis-benchmark/",
    f"{SITE_URL}/ai-api-rate-limits-explained/",
    f"{SITE_URL}/the-ai-price-war-racing-to-zero/",
    f"{SITE_URL}/claude-4-6-opus-launched-pricing-performance/",
    f"{SITE_URL}/google-gemini-api-pricing-may-2026/",
    f"{SITE_URL}/openai-api-pricing-may-2026/",
    f"{SITE_URL}/grok-xai-api-pricing-may-2026/",
    f"{SITE_URL}/ai-model-pricing-comparison-gemini-openai-grok-claude-2026/",
    f"{SITE_URL}/google-nano-banana-imagen-4-image-generation-pricing-may-2026/",
    f"{SITE_URL}/google-gemini-tts-speech-audio-api-pricing-may-2026/",
    f"{SITE_URL}/google-veo-lyria-video-music-generation-api-pricing-may-2026/",
    # Older posts (re-index)
    f"{SITE_URL}/google-gemini-ai-api-pricing-explained-october-2025/",
    f"{SITE_URL}/openai-api-pricing-comparison-october-2025/",
    f"{SITE_URL}/grok-api-latest-llms-pricing-october-2025/",
    f"{SITE_URL}/choosing-best-llm-api-provider-to-build-ai-agents-in-2025/",
    f"{SITE_URL}/why-is-google-gemini-api-the-best-choice-to-begin-generative-ai-journey-in-2025/",
    f"{SITE_URL}/why-google-gemini-2.5-pro-api-provides-best-and-cost-effective-solution-for-ocr-and-document-intelligence/",
    f"{SITE_URL}/top-use-cases-of-google-gemini-ai-in-healthcare-industry/",
    f"{SITE_URL}/build-everything-with-gemini-2.5-api-Image_Analysis_Use_Cases_and_Prompts/",
    f"{SITE_URL}/generative-ai-gemini-vs-other-api-providers-cost-comparison/",
    f"{SITE_URL}/comparison-of-google-ocr-vs-aws-and-azure-ocr-apis-cost-and-speed-comparison/",
    f"{SITE_URL}/openai-api-updates-and-pricing-october-2025/",
    f"{SITE_URL}/top-llm-api-provider-to-build-ai-applications-and-ai-agents/",
    f"{SITE_URL}/google-gemini-nano-banana-image-generation-api-pricing/",
    f"{SITE_URL}/simplify-your-workflow-with-a-barcode-reader-generator/",
    # Homepage
    f"{SITE_URL}/",
]


def submit_url(service, url, action="URL_UPDATED"):
    """Submit a single URL to the Google Indexing API."""
    body = {"url": url, "type": action}
    try:
        response = service.urlNotifications().publish(body=body).execute()
        print(f"  ✅ {url}")
        print(f"     Notified: {response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('notifyTime', 'N/A')}")
        return True
    except Exception as e:
        print(f"  ❌ {url}")
        print(f"     Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Submit URLs to Google Indexing API")
    parser.add_argument("--credentials", "-c", required=True, help="Path to service account JSON key")
    parser.add_argument("--urls", "-u", nargs="*", help="Specific URLs to submit (default: all)")
    args = parser.parse_args()

    # Authenticate
    try:
        credentials = service_account.Credentials.from_service_account_file(
            args.credentials, scopes=SCOPES
        )
        service = build("indexing", "v3", credentials=credentials)
        print("🔑 Authenticated successfully!\n")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\nMake sure:")
        print("1. The JSON file is a valid Google Cloud service account key")
        print("2. The Indexing API is enabled in your Google Cloud project")
        print("3. The service account email is added as Owner in Google Search Console")
        sys.exit(1)

    urls_to_submit = args.urls if args.urls else URLS
    
    print(f"📤 Submitting {len(urls_to_submit)} URLs for indexing...\n")
    
    success = 0
    failed = 0
    for url in urls_to_submit:
        if submit_url(service, url):
            success += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully submitted: {success}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(urls_to_submit)}")


if __name__ == "__main__":
    main()
