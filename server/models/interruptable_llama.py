from typing import Optional, List, Generator, Dict

from langchain import LlamaCpp
from langchain.callbacks.manager import CallbackManagerForLLMRun


class InterruptableLlamaCpp(LlamaCpp):
    def stream(
            self,
            prompt: str,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> Generator[Dict, None, None]:
        params = self._get_parameters(stop)
        result = self.client(prompt=prompt, stream=True, **params)
        for chunk in result:
            token = chunk["choices"][0]["text"]
            log_probs = chunk["choices"][0].get("logprobs", None)
            if run_manager:
                run_manager.on_llm_new_token(
                    token=token, verbose=self.verbose, log_probs=log_probs
                )
                try:  # this is the extra code so we can abort
                    handler = run_manager.handlers[0]
                    abort = handler.abort
                except (NameError, IndexError, AttributeError):
                    abort = False
                if abort:
                    print('Aborting...')
                    break  # the rest of this method is equivalent to LlamaCpp
            yield chunk
