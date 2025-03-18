import json
import os

from openai import OpenAI


class AI:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.vector_stores = []

    def add_file(self, file, data):
        # Upload file to OpenAI
        # Add to vector sector
        # Add vector ID to vector store list
        file_path = file.name
        uploaded_file = self.client.files.create(
            file=(file_path, data),
            purpose="assistants"
        )

        vector_store = self.client.vector_stores.create(
            name=file_path,
        )

        self.client.vector_stores.files.create_and_poll(
            vector_store_id=vector_store.id,
            file_id=uploaded_file.id
        )
        self.vector_stores.append(vector_store.id)
        return [vector_store.id, uploaded_file.id]

    def create_thread(self, ):
        thread = self.client.beta.threads.create()
        thread_id = thread.id
        print("vector secote", self.vector_stores)
        thread = self.client.beta.threads.update(
            thread_id,
            tool_resources={
                "file_search": {"vector_store_ids": self.vector_stores}},
            metadata=thread.metadata
        )
        print(thread)
        # time.sleep(2)
        return thread.id

    @staticmethod
    def get_assistant_id():
        return "asst_PPEXBDqzOxPNVHCBj6wKRtM9"

    def run(self, thread_id: str, additional_instructions: str = ""):

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=self.get_assistant_id(),
            additional_instructions=additional_instructions,
            response_format={"type": "json_object"},
        )
        return run

    def add_message_to_thread(self, thread_id: str, message: str):
        # try:
        #     print("canceling existing run")
        #     self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id="run_EVZOB6zC8ODtkNGr2utZZmKm")
        #     print("Cancelled existing run")
        # except Exception as e:
        #     print(f"Failed to cancel existing run: {e}")
        thread = self.client.beta.threads.retrieve(thread_id)
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            content=message,
            role="user"
        )

        return thread

    def get_function_reference(self, function_name):
        return "function"

    def process_ai_response(self, run):
        print(run.status)
        if run.status == "requires_action":
            print("here")
            function_responses = list()
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                arguments = tool.function.arguments
                # parse string to dict
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as e:
                    print(f"Error parsing arguments: {e}")
                    arguments = {}
                _function = self.get_function_reference(tool.function.name)
                try:
                    function_response = _function(**arguments, user=self.user)
                except Exception as e:
                    print(f"Error processing function: {e}")
                    function_response = "Error processing function"
                if isinstance(function_response, str):
                    function_responses.append({
                        "tool_call_id": tool.id,
                        "output": function_response
                    })
                else:
                    function_responses.append({
                        "tool_call_id": tool.id,
                        "output": "Error processing function"
                    })

            return self.process_ai_response(
                self.client.beta.threads.runs.submit_tool_outputs_and_poll(tool_outputs=function_responses,
                                                                           run_id=run.id,
                                                                           thread_id=run.thread_id))

        elif run.status == "completed":
            response = self.client.beta.threads.messages.list(thread_id=run.thread_id).data[0]
            return response.content[0].text.value
