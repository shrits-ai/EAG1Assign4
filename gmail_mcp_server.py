# gmail_mcp_server.py
import os.path
import sys
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText # Needed for creating email message

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# --- Gmail Authentication Setup ---
# *** IMPORTANT: Scope changed to allow sending! ***
SCOPES = ['https://www.googleapis.com/auth/gmail.send'] # Changed from readonly
# Path to your downloaded client secrets file
CREDENTIALS_PATH = 'credentials.json'
# Path where the token will be stored after first authorization
# *** Delete the old token.json file before running this script! ***
TOKEN_PATH = 'token.json'

def get_gmail_service():
    """Shows basic usage of the Gmail API. Authenticates user and returns service object."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"Error loading token file ({TOKEN_PATH}): {e}. Will re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
                print("Credentials refreshed.")
            except Exception as e:
                print(f"An error occurred during token refresh: {e}")
                # Attempt to delete potentially corrupted token file if refresh fails
                if os.path.exists(TOKEN_PATH):
                    try:
                        os.remove(TOKEN_PATH)
                        print(f"Removed potentially invalid {TOKEN_PATH} due to refresh error.")
                    except Exception as del_e:
                        print(f"Error removing token file after refresh error: {del_e}")
                creds = None # Force re-authentication
        # Only attempt full flow if no valid/refreshed creds
        if not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_PATH):
                 raise FileNotFoundError(f"ERROR: Credentials file not found at {CREDENTIALS_PATH}. "
                                         "Please download your OAuth 2.0 Desktop Client credentials "
                                         "and save them as credentials.json in the same directory.")
            try:
                print("No valid credentials found, initiating OAuth flow (requires browser interaction)...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
                print("OAuth flow completed successfully.")
                # Save the credentials for the next run
                try:
                    with open(TOKEN_PATH, 'wb') as token:
                        pickle.dump(creds, token)
                    print(f"Credentials saved to {TOKEN_PATH}")
                except Exception as e:
                    print(f"Error saving credentials to {TOKEN_PATH}: {e}")

            except Exception as e:
                 print(f"An error occurred during OAuth flow: {e}")
                 raise

    try:
        service = build('gmail', 'v1', credentials=creds)
        print("Gmail service built successfully.")
        return service
    except Exception as e:
        print(f"An error occurred building the Gmail service: {e}")
        raise

# --- MCP Server Setup ---
mcp = FastMCP("GmailSenderAgent")
gmail_service = None # Initialize globally

# --- NEW: Send Email Tool ---
@mcp.tool()
async def send_email(to: str, subject: str, body: str) -> dict:
    """
    Sends an email message.
    Requires 'to' address, 'subject', and 'body' text.
    """
    global gmail_service
    print(f"CALLED: send_email(to='{to}', subject='{subject}', body='{body[:50]}...')") # Log truncated body
    if not gmail_service:
        return {"content": [TextContent(type="text", text="Error: Gmail service not initialized.")]}

    try:
        # Create the email message object
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        # 'me' can be used to indicate the authenticated user's email address
        # Getting the actual email address requires another scope (gmail.readonly or userinfo.email)
        # For sending, 'From' is usually automatically set to the authenticated user by Gmail.
        # message['from'] = 'me' # Usually not needed

        # Encode the message in base64url format
        raw_message_bytes = message.as_bytes()
        encoded_message = base64.urlsafe_b64encode(raw_message_bytes).decode()
        body_payload = {'raw': encoded_message}

        # Call the Gmail API to send the message
        sent_message = gmail_service.users().messages().send(
            userId='me', # 'me' indicates the authenticated user
            body=body_payload
        ).execute()

        print(f"Message sent successfully. ID: {sent_message.get('id')}")
        return {"content": [TextContent(type="text", text=f"Email sent successfully to {to} with subject '{subject}'. Message ID: {sent_message.get('id')}")]}

    except HttpError as error:
        error_details = getattr(error, 'content', str(error)).decode("utf-8")
        print(f'An HTTP error occurred sending email: {error_details}')
        return {"content": [TextContent(type="text", text=f"An HTTP error occurred sending email: {error_details}")]}
    except Exception as e:
         print(f'An unexpected error occurred sending email: {e}')
         return {"content": [TextContent(type="text", text=f"An unexpected error occurred sending email: {e}")]}

# Keep list_emails and get_email if you want the agent to be able to read *and* send
# Or remove them if you only want sending capability
@mcp.tool()
async def list_emails(query: str = None, max_results: int = 10) -> dict:
    """Lists email messages matching a query (requires readonly or modify scope)."""
    # ... (Implementation from previous server script - requires appropriate scope) ...
    # NOTE: This will fail if SCOPES is only gmail.send.
    # Add gmail.readonly back to SCOPES if read capability is also needed.
    if 'gmail.readonly' not in SCOPES and 'gmail.modify' not in SCOPES:
         return {"content": [TextContent(type="text", text="Error: Insufficient scope to list emails. Requires gmail.readonly or gmail.modify.")]}
    # ... (rest of list_emails implementation) ...
    # Placeholder implementation if readonly scope is missing:
    return {"content": [TextContent(type="text", text="List emails requires readonly scope, which is not currently enabled.")]}


@mcp.tool()
async def get_email(message_id: str, body_format: str = 'full') -> dict:
    """Gets the content of a specific email message by ID (requires readonly or modify scope)."""
    # ... (Implementation from previous server script - requires appropriate scope) ...
    # NOTE: This will fail if SCOPES is only gmail.send.
    # Add gmail.readonly back to SCOPES if read capability is also needed.
    if 'gmail.readonly' not in SCOPES and 'gmail.modify' not in SCOPES:
         return {"content": [TextContent(type="text", text="Error: Insufficient scope to get email. Requires gmail.readonly or gmail.modify.")]}
    # ... (rest of get_email implementation) ...
    # Placeholder implementation if readonly scope is missing:
    return {"content": [TextContent(type="text", text="Get email requires readonly scope, which is not currently enabled.")]}


# --- Main Execution ---
if __name__ == "__main__":
    print("STARTING Gmail Sender MCP Server")
    print("Attempting to initialize Gmail service...")
    try:
        # Initialize service when server starts
        gmail_service = get_gmail_service()
        if not gmail_service:
             print("FATAL: Failed to initialize Gmail Service. Exiting.")
             sys.exit(1)
        print("Gmail Service Initialized.")
    except Exception as auth_error:
         print(f"FATAL: Authentication/Initialization Error: {auth_error}")
         sys.exit(1)


    # Check if running with mcp dev command
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution