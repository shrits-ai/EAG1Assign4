# MCP Agent Examples: Gmail Sending & macOS Keynote Control

This repository contains examples of agents built using the Model Context Protocol (MCP) and Google's Generative AI (Gemini).

---

## Example 1: MCP Gmail Sending Agent

### Description

This agent uses MCP and Google Gemini to send emails via the Gmail API. The agent takes a predefined request (recipient, subject, body) specified in the client script, uses the LLM to understand the request, and calls an MCP server tool that leverages the Gmail API to send the email.

The client script includes detailed logging of the interaction between the client, the LLM, and the MCP server.

### Features (Gmail Agent)

* **MCP Server:** Provides tools accessible to an MCP client/LLM.
    * `send_email(to: str, subject: str, body: str)`: Sends an email using the authenticated user's Gmail account.
    * (Optional placeholders for `list_emails` and `get_email` exist but require different OAuth scopes).
* **MCP Client:**
    * Connects to the local MCP server.
    * Uses Google Gemini (`gemini-1.5-flash`) to interpret a hardcoded user query.
    * Instructs the LLM to call the `send_email` tool via the server.
    * Provides detailed, timestamped logs of the entire process.
* **Gmail Integration:** Uses the official Google API Client Library for Python and OAuth 2.0 (Desktop App flow) for secure authentication.

### Prerequisites (Gmail Agent)

1.  **Python:** Python 3.9 or higher recommended.
2.  **Google Cloud Project:**
    * A Google Cloud project must be created.
    * The **Gmail API** must be enabled for this project.
3.  **OAuth 2.0 Credentials:** You need to configure OAuth 2.0 credentials for a **Desktop application** within your Google Cloud project:
    * **Configure OAuth Consent Screen:** Set up the consent screen (User Type: likely "External"). Add your email address as a **Test User** while the app is in "Testing" mode.
    * **Create OAuth Client ID:** Create credentials of type "Desktop app".
    * **Download `credentials.json`:** Download the client secret JSON file and save it as `credentials.json` in the root of this project directory.
    * **Scopes:** Ensure the consent screen is configured with the required scope: `https://www.googleapis.com/auth/gmail.send`.

### Installation (Gmail Agent)

1.  **Get Files:** Ensure you have `gmail_mcp_server_send.py` and `gmail_mcp_client_send.py`.
2.  **Install Libraries:** Open a terminal in the project directory and install the required Python packages:
    ```bash
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib mcp google-generativeai python-dotenv Pillow
    ```

### Setup (Gmail Agent)

1.  **Google Credentials:** Place the downloaded `credentials.json` file in the root of the project directory.
2.  **Gemini API Key:** Create a file named `.env` in the project root directory. Add your Google Generative AI API key to it:
    ```dotenv
    GEMINI_API_KEY=YOUR_API_KEY_HERE
    ```
3.  **Configure Email Request:** Open `gmail_mcp_client_send.py` and find the `user_query` variable. **Modify the recipient email address, subject, and body** to your desired values.
4.  **Delete Old Token (IMPORTANT):** If you have run previous versions of the server (especially with different scopes like `gmail.readonly`), **delete the `token.json` file** from the project directory before the first run. This forces re-authentication with the correct `gmail.send` scope.

### Running the Gmail Agent

1.  **Open Terminal:** Navigate to the project directory in your terminal.
2.  **Run Client Script:** Execute the client script:
    ```bash
    python3 gmail_mcp_client_send.py
    ```
3.  **First-Time Authentication:** Follow the on-screen instructions. Your web browser should open automatically, prompting you to log in and **grant permission to "Send email on your behalf"**. After authorization, `token.json` will be saved.
4.  **Agent Execution:** Observe the logs in the terminal showing the LLM interaction and the result of the `send_email` tool call. Check the recipient's inbox.

---

## Example 2: MCP macOS Keynote Agent

### Description

This agent demonstrates controlling the Apple Keynote application on macOS using MCP and Google Gemini. The agent interprets a request (defined in the client script) to perform actions like opening Keynote, creating slides, drawing shapes, and adding text by calling tools on an MCP server that uses AppleScript.

### Features (Keynote Agent)

* **MCP Server:** Provides tools to control Keynote via AppleScript.
    * `open_keynote()`: Opens the Keynote application.
    * `create_blank_keynote_slide()`: Ensures a new or blank slide is ready.
    * `draw_keynote_rectangle(x1: int, y1: int, width: int, height: int)`: Draws a rectangle.
    * `add_text_in_keynote(text: str, x: int, y: int, width: int, height: int)`: Adds a text box.
* **MCP Client:**
    * Connects to the local MCP server.
    * Uses Google Gemini (`gemini-1.5-flash`) to interpret a hardcoded user query about Keynote actions.
    * Instructs the LLM to call the Keynote tools sequentially via the server.
    * Provides detailed, timestamped logs.

### Prerequisites (Keynote Agent)

1.  **macOS:** This agent is designed specifically for macOS.
2.  **Apple Keynote:** The Keynote application must be installed.
3.  **Python:** Python 3.9 or higher recommended.
4.  **Permissions:** The first time you run the script, macOS will likely ask for permission for your terminal/IDE to control Keynote. You must grant these automation permissions.

### Installation (Keynote Agent)

1.  **Get Files:** Ensure you have `mac_keynote_server.py` and `mac_keynote_client.py`.
2.  **Install Libraries:** Open a terminal in the project directory and install the required Python packages:
    ```bash
    pip install --upgrade mcp google-generativeai python-dotenv Pillow
    ```
    *(Note: No extra GUI automation libraries like `pyautogui` are needed for this AppleScript-based version).*

### Setup (Keynote Agent)

1.  **Gemini API Key:** Create a file named `.env` in the project root directory (or ensure it exists from the Gmail setup). Add your Google Generative AI API key:
    ```dotenv
    GEMINI_API_KEY=YOUR_API_KEY_HERE
    ```
2.  **Configure Keynote Request:** Open `mac_keynote_client.py` and find the `user_query` variable. Modify it to describe the sequence of Keynote actions you want the agent to perform (e.g., drawing specific shapes, adding specific text at certain coordinates). Remember that coordinates are in points and may require experimentation.

### Running the Keynote Agent

1.  **Open Terminal:** Navigate to the project directory in your terminal.
2.  **Run Client Script:** Execute the client script:
    ```bash
    python3 mac_keynote_client.py
    ```
3.  **Grant Permissions (First Run):** If prompted by macOS, allow the script (running via your terminal or IDE) to control Keynote.
4.  **Agent Execution:** Observe the logs in the terminal showing the LLM interaction as it calls the Keynote tools sequentially. Watch Keynote on your screen to see the actions being performed.

---
