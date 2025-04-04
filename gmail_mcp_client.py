# gmail_mcp_client.py
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
import google.generativeai as genai # Correct import
from concurrent.futures import TimeoutError
import shlex
import datetime # For logging timestamp

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")

# Configure the Generative AI client
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash') # Use a capable model


max_iterations = 5 # Sending should be quicker than reading typically
last_response = None
iteration = 0
iteration_history = [] # Store history of calls and results


# --- Enhanced Logging ---
def log_event(message: str):
    """Prints a message with a timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

async def generate_with_timeout(prompt_parts: list, timeout=45):
    """Generate content with a timeout using the configured model, with logging."""
    log_event(f"--- Starting LLM generation (Iteration {iteration + 1}) ---")
    log_event("Sending Prompt Content:")
    for i, part in enumerate(prompt_parts):
        log_event(f"  Prompt Part {i+1}:\n---\n{part}\n---")

    try:
        response = await asyncio.wait_for(
            model.generate_content_async(prompt_parts),
            timeout=timeout
        )
        log_event("--- LLM generation completed ---")
        log_event(f"LLM Raw Response:\n---\n{response}\n---")
        return response
    except TimeoutError:
        log_event("--- LLM generation timed out! ---")
        raise
    except Exception as e:
        log_event(f"--- Error in LLM generation: {e} ---")
        raise


def reset_state():
    """Reset global variables"""
    global last_response, iteration, iteration_history
    last_response = None
    iteration = 0
    iteration_history = []
    log_event("--- Global state reset ---")


async def main():
    reset_state()
    log_event("--- Starting main execution ---")
    try:
        log_event("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command=sys.executable,
            # *** Make sure to run the correct server script ***
            args=["gmail_mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            log_event("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                log_event("Session created, initializing...")
                await session.initialize()

                log_event("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                log_event(f"Successfully retrieved {len(tools)} tools.")

                log_event("Creating system prompt...")
                tools_description = []
                for i, tool in enumerate(tools):
                    # Basic tool description generation
                    try:
                        params = tool.inputSchema.get('properties', {})
                        desc = getattr(tool, 'description', 'No description available').strip()
                        name = getattr(tool, 'name', f'tool_{i}')
                        param_details = [f"{p_name}: {p_info.get('type', 'unknown')}" for p_name, p_info in params.items()]
                        params_str = ', '.join(param_details) if param_details else 'no parameters'
                        tools_description.append(f"{i+1}. {name}({params_str}) - {desc}")
                    except Exception as e:
                         log_event(f"Warning: Error processing tool {i} ({getattr(tool, 'name', 'unknown')}): {e}")
                         tools_description.append(f"{i+1}. Error processing tool {getattr(tool, 'name', 'unknown')}")


                tools_description_str = "\n".join(tools_description)
                log_event("--- Available Tools ---")
                log_event(f"\n{tools_description_str}") # Log available tools
                log_event("-----------------------")

                # --- System Prompt focused on Sending ---
                system_prompt = f"""You are an agent designed to send emails via Gmail using the available tools.

Available tools:
{tools_description_str}

Your goal is to follow the user's request to send an email.
You MUST respond with EXACTLY ONE line in one of these formats (no additional text, explanations, or markdown formatting):

1.  To call a function:
    FUNCTION_CALL: function_name|param1|param2|...
    - Parameters MUST be in the correct order specified in the tool description (to, subject, body for send_email).

2.  When the email has been successfully sent (based on tool result):
    FINAL_ANSWER: Email sent successfully. [Include details from tool result if available, like Message ID]

Important Rules:
- Use the `send_email` tool to fulfill the user's request.
- Extract the recipient address, subject, and body from the user query to use as parameters for `send_email`.
- Only output `FINAL_ANSWER:` after the `send_email` tool confirms success.
- If the `send_email` tool returns an error, report it using `FINAL_ANSWER: Task failed. Error: [error message from history]`.

Begin!"""

                # --- User Query Focused on Sending ---
                # !!! IMPORTANT: Replace 'your_email@example.com' with your actual email address !!!
                user_query = "Please send an email to your_email@example.com with the subject 'MCP Agent Test' and the body 'This email was sent by the MCP Gmail agent.'"

                log_event(f"\n--- User Query ---\n{user_query}\n------------------")

                global iteration, last_response, iteration_history

                current_prompt_parts = [system_prompt, f"\nUser Query: {user_query}"]

                while iteration < max_iterations:
                    log_event(f"\n<<< --- Iteration {iteration + 1} --- >>>")

                    # Add history to prompt if needed (less critical for simple send task)
                    if iteration_history:
                         history_str = "\n".join(iteration_history)
                         current_prompt_parts = [system_prompt, f"\nUser Query: {user_query}", f"\nHistory:\n{history_str}\n\nWhat is the next step?"]
                    else:
                         current_prompt_parts = [system_prompt, f"\nUser Query: {user_query}", "\nWhat is the first step?"]


                    try:
                        response = await generate_with_timeout(current_prompt_parts)
                        # Extract text response
                        if hasattr(response, 'text'):
                            response_text = response.text.strip()
                        elif hasattr(response, 'candidates') and response.candidates:
                             content = response.candidates[0].content
                             if hasattr(content, 'parts') and content.parts:
                                 response_text = content.parts[0].text.strip()
                             else: response_text = "Error: No text parts in LLM response."
                        else: response_text = "Error: Unexpected LLM response format."

                        log_event(f"LLM Response Text Line: '{response_text}'")

                        # Clean potential markdown
                        if response_text.startswith("```") and response_text.endswith("```"):
                           response_text = response_text[3:-3].strip()
                        if response_text.startswith("`") and response_text.endswith("`"):
                            response_text = response_text[1:-1].strip()


                    except Exception as e:
                        log_event(f"Failed to get LLM response: {e}")
                        iteration_history.append(f"Iteration {iteration + 1}: Failed to get LLM response: {e}")
                        break

                    if response_text.startswith("FUNCTION_CALL:"):
                        try:
                            _, function_info = response_text.split(":", 1)
                            parts = function_info.split('|') # Simple split, assuming no '|' in params
                            func_name = parts[0].strip()
                            params = [p.strip() for p in parts[1:]]

                            log_event(f"LLM requests FUNCTION_CALL: {func_name} with params: {params}")

                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                raise ValueError(f"Unknown tool '{func_name}' requested by LLM.")

                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            expected_params = list(schema_properties.keys())

                            # Basic parameter count check for send_email
                            if func_name == "send_email" and len(params) != 3:
                                 raise ValueError(f"Incorrect number of parameters for send_email. Expected 3 (to, subject, body), got {len(params)}.")

                            # Simple assignment based on expected order for send_email
                            if func_name == "send_email":
                                arguments['to'] = params[0]
                                arguments['subject'] = params[1]
                                arguments['body'] = params[2]
                            else: # Add handling for other tools if they exist
                                 # Fallback or more generic handling needed if other tools are present
                                 log_event(f"Warning: Parameter mapping not explicitly defined for tool {func_name}. Attempting basic assignment.")
                                 if len(params) > len(expected_params): params = params[:len(expected_params)]
                                 for i, param_name in enumerate(expected_params):
                                     if i < len(params): arguments[param_name] = params[i]


                            log_event(f"Executing MCP tool '{func_name}' with arguments: {arguments}")
                            result = await session.call_tool(func_name, arguments=arguments)
                            log_event(f"MCP Raw Result: {result}")

                            if result.content and isinstance(result.content, list) and hasattr(result.content[0], 'text'):
                                iteration_result = result.content[0].text
                            else:
                                iteration_result = "Tool executed, no standard text result."
                            log_event(f"Tool Result Text (for history):\n---\n{iteration_result}\n---")

                            history_summary = f"Iteration {iteration + 1}: Called {func_name}(...). Result: {iteration_result[:200]}..."
                            iteration_history.append(history_summary)
                            last_response = iteration_result

                            if "error" in iteration_result.lower():
                                log_event(f"Tool reported an error: {iteration_result}. Allowing LLM to handle.")

                        except Exception as e:
                            log_event(f"Error during function call processing: {e}")
                            import traceback
                            log_event(f"Traceback:\n{traceback.format_exc()}")
                            iteration_history.append(f"Iteration {iteration + 1}: Client Error processing '{response_text}': {e}")
                            break

                    elif response_text.startswith("FINAL_ANSWER:"):
                        final_message = response_text.split(":", 1)[1].strip()
                        log_event(f"\n=== Agent Execution Complete ===")
                        log_event(f"Final Answer from LLM: {final_message}")
                        iteration_history.append(f"Iteration {iteration + 1}: Received FINAL_ANSWER: {final_message}")
                        break

                    else:
                        log_event(f"Warning: LLM response format unexpected: '{response_text}'")
                        iteration_history.append(f"Iteration {iteration + 1}: Unexpected LLM response format: '{response_text}'")

                    iteration += 1
                    if iteration >= max_iterations:
                        log_event("\n--- Max iterations reached ---")
                        iteration_history.append(f"Iteration {iteration}: Max iterations reached.")


    except Exception as e:
        log_event(f"\n--- Error in main execution ---")
        log_event(f"{type(e).__name__}: {e}")
        import traceback
        log_event(f"Traceback:\n{traceback.format_exc()}")
    finally:
        log_event("\n--- Final Execution History ---")
        for line in iteration_history:
            log_event(line)
        log_event("-----------------------------")
        reset_state()
        log_event("--- Main execution finished ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")