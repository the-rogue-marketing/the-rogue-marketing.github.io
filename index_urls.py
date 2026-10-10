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
import os
import re
import sys
import yaml

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/indexing"]

SITE_URL = "https://the-rogue-marketing.github.io"

def get_all_site_urls():
    urls = {SITE_URL + "/"}
    
    # 1. Parse posts
    repo_root = os.path.dirname(os.path.abspath(__file__))
    posts_dir = os.path.join(repo_root, "_posts")
    if os.path.exists(posts_dir):
        for filename in os.listdir(posts_dir):
            if not filename.endswith((".md", ".html")):
                continue
            path = os.path.join(posts_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                permalink = None
                if match:
                    frontmatter = yaml.safe_load(match.group(1))
                    if isinstance(frontmatter, dict):
                        permalink = frontmatter.get("permalink")
                
                if not permalink:
                    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)\.(?:md|html)$", filename)
                    if m:
                        title_slug = m.group(1)
                        permalink = f"/{title_slug}/"
                    else:
                        title_slug = os.path.splitext(filename)[0]
                        permalink = f"/{title_slug}/"
                
                if permalink:
                    permalink = str(permalink)
                    if not permalink.startswith("/"):
                        permalink = "/" + permalink
                    if not permalink.endswith("/"):
                        permalink = permalink + "/"
                    urls.add(SITE_URL + permalink)
            except Exception as e:
                print(f"⚠️ Error parsing post {filename}: {e}")

    # 2. Parse pages
    pages_dir = os.path.join(repo_root, "pages")
    if os.path.exists(pages_dir):
        for filename in os.listdir(pages_dir):
            if not filename.endswith((".md", ".html")):
                continue
            path = os.path.join(pages_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                permalink = None
                if match:
                    frontmatter = yaml.safe_load(match.group(1))
                    if isinstance(frontmatter, dict):
                        permalink = frontmatter.get("permalink")
                
                if not permalink:
                    slug = os.path.splitext(filename)[0]
                    permalink = f"/{slug}/"
                
                if permalink:
                    permalink = str(permalink)
                    if not permalink.startswith("/"):
                        permalink = "/" + permalink
                    if not permalink.endswith("/"):
                        permalink = permalink + "/"
                    urls.add(SITE_URL + permalink)
            except Exception as e:
                print(f"⚠️ Error parsing page {filename}: {e}")

    return sorted(list(urls))

URLS = get_all_site_urls()



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
