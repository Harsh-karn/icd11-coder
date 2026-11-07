"""SDK wire-format contracts using synthetic HTTP responses, no API keys/network."""
import asyncio
import json
import os
import unittest
from unittest.mock import patch
import httpx
import httpx2
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from src.llm_coder import LLMCoder

SYSTEM_ENV_KEYS = {"SYSTEMROOT", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PATH", "TEMP", "TMP", "SystemDrive"}

def get_base_env():
    return {k: v for k, v in os.environ.items() if k in SYSTEM_ENV_KEYS}

class Providers(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_success_and_failure(self):
        base_env = get_base_env()
        for provider in ['openai','anthropic']:
            for status in [200,401,429,500,"timeout"]:
                transport_module = httpx if provider == "openai" else httpx2
                seen=[]
                def handler(request):
                    seen.append(json.loads(request.content))
                    if status == "timeout":
                        raise transport_module.ReadTimeout("synthetic timeout", request=request)
                    if status!=200:
                        return transport_module.Response(status,json={'error':{'type':'rate_limit_error','message':'synthetic'}})
                    if provider=='openai':
                        data={'id':'fixture','object':'chat.completion','created':0,'model':'gpt-4o-mini','choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':'{"codes":["CA00"]}'}}],'usage':{'prompt_tokens':10,'completion_tokens':8,'total_tokens':18}}
                    else:
                        data={'id':'fixture','type':'message','role':'assistant','model':'claude-haiku-4-5-20251001','content':[{'type':'text','text':'{"codes":["CA00"]}'}],'stop_reason':'end_turn','usage':{'input_tokens':10,'output_tokens':8}}
                    return transport_module.Response(200,json=data)
                with patch.dict(os.environ, base_env, clear=True): coder=LLMCoder({'CA00'})
                client=transport_module.AsyncClient(transport=transport_module.MockTransport(handler))
                sdk=AsyncOpenAI if provider=='openai' else AsyncAnthropic
                setattr(coder,'async_'+provider,sdk(api_key='synthetic-local-test',http_client=client,max_retries=0))
                result=await coder.predict_async('Acute nasopharyngitis',[{'code':'CA00','title':'Acute nasopharyngitis'}])
                self.assertEqual(['CA00'] if status==200 else [],result)
                self.assertEqual(1,len(seen));self.assertEqual(150,seen[0]['max_tokens'])
                self.assertGreater(coder.reserved,0)
                self.assertEqual(10 if status == 200 else 0, coder.input_tokens)
                self.assertEqual(8 if status == 200 else 0, coder.output_tokens)
                await coder.close()

    async def test_budget_concurrent_requests(self):
        base_env = get_base_env()
        with patch.dict(os.environ,{**base_env, 'ICD_BUDGET_USD':'.01'},clear=True): coder=LLMCoder({'CA00'})
        calls=[]
        def handler(request):
            calls.append(1)
            return httpx.Response(500,json={'error':{'message':'synthetic'}})
        coder.async_openai=AsyncOpenAI(api_key='synthetic-local-test',max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        await asyncio.gather(*(coder.predict_async('cold',[{'code':'CA00','title':'cold'}]) for _ in range(8)))
        self.assertLessEqual(coder.reserved,.01);self.assertEqual(coder.calls,len(calls));self.assertGreater(len(calls),0)
        await coder.close()

    async def test_https_proxy_is_honored(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        destinations = []
        class Proxy(BaseHTTPRequestHandler):
            def do_CONNECT(self):
                destinations.append(self.path)
                self.send_error(403, "Synthetic proxy denial")
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_env = get_base_env()
        try:
            for key, host in [("OPENAI_API_KEY", "api.openai.com:443"),
                              ("ANTHROPIC_API_KEY", "api.anthropic.com:443")]:
                env = {**base_env, key: "synthetic-local-test", "HTTPS_PROXY": f"http://127.0.0.1:{server.server_port}"}
                with patch.dict(os.environ, env, clear=True):
                    coder = LLMCoder({"CA00"})
                    try:
                        result = await coder.predict_async("cold", [{"code": "CA00", "title": "cold"}])
                        self.assertEqual([], result)
                        self.assertIn(host, destinations)
                    finally:
                        await coder.close()
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join()
