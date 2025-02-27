import asyncio
import logging

import httpx
from httpx import Response

from genai._version import version
from genai.options import Options
from genai.services.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

__all__ = ["RequestHandler"]


class RequestHandler:
    @staticmethod
    def _metadata(
        method: str,
        key: str,
        model_id: str = None,
        inputs: list = None,
        parameters: dict = None,
        options: Options = None,
    ) -> tuple[dict, dict]:
        """General function to build header and/or json_data for /post and /get requests.

        Args:
            method (str): Request type. Currently accepts GET or POST
            key (str): API key for authorization.
            model_id (str, optional): The id of the language model to be queried. Defaults to None.
            inputs (list, optional): List of inputs to be queried. Defaults to None.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.
            options (Options, optional): Additional parameters to pass in the query payload. Defaults to None.

        Returns:
            tuple[dict,dict]: Headers, json_data for request
        """

        headers = {
            "Authorization": f"Bearer {key}",
            "x-request-origin": f"python-sdk/{version}",
        }
        json_data = {}

        if method == "POST" or method == "PUT":
            headers["Content-Type"] = "application/json"

            if model_id is not None:
                json_data["model_id"] = model_id

            if inputs is not None:
                json_data["inputs"] = inputs

            if parameters is not None:
                json_data["parameters"] = parameters

            if options is not None:
                for key in options.keys():
                    json_data[key] = options[key]

        if method == "PATCH":
            headers["Content-Type"] = "application/json"

        return headers, json_data

    @staticmethod
    async def async_post(
        endpoint: str,
        key: str,
        model_id: str = None,
        inputs: list = None,
        parameters: dict = None,
        options: Options = None,
    ):
        """Low level API for async /post request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            model_id (str, optional): The id of the language model to be queried. Defaults to None.
            inputs (list, optional): List of inputs to be queried. Defaults to None.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, json_data = RequestHandler._metadata(
            method="POST", key=key, model_id=model_id, inputs=inputs, parameters=parameters, options=options
        )
        response = None
        async with httpx.AsyncClient(timeout=ConnectionManager.TIMEOUT) as client:
            response = await client.post(endpoint, headers=headers, json=json_data)
        return response

    @staticmethod
    async def async_patch(endpoint: str, key: str, json_data: dict = None) -> Response:
        """Low level API for /patch request to REST API.

        Currently only used for TOU endpoint.

        Args:
            endpoint (str):
            key (str)
            payload: (dict, optional)

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, json_data = RequestHandler._metadata(method="PATCH", key=key)
        response = None
        async with httpx.AsyncClient(timeout=ConnectionManager.TIMEOUT) as client:
            response = await client.patch(endpoint, headers=headers, json=json_data)
        return response

    @staticmethod
    async def async_generate(
        endpoint: str,
        key: str,
        model_id: str = None,
        inputs: list = None,
        parameters: dict = None,
        options: Options = None,
    ):
        """Low level API for async /generate request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            model_id (str, optional): The id of the language model to be queried. Defaults to None.
            inputs (list, optional): List of inputs to be queried. Defaults to None.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, json_data = RequestHandler._metadata(
            method="POST", key=key, model_id=model_id, inputs=inputs, parameters=parameters, options=options
        )
        response = None
        for attempt in range(0, ConnectionManager.MAX_RETRIES_GENERATE):
            response = await ConnectionManager.async_generate_client.post(endpoint, headers=headers, json=json_data)
            if response.status_code in [httpx.codes.SERVICE_UNAVAILABLE, httpx.codes.TOO_MANY_REQUESTS]:
                await asyncio.sleep(2 ** (attempt + 1))
            else:
                break
        return response

    @staticmethod
    async def async_tokenize(
        endpoint: str,
        key: str,
        model_id: str = None,
        inputs: list = None,
        parameters: dict = None,
        options: Options = None,
    ):
        """Low level API for async /tokenize request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            model_id (str, optional): The id of the language model to be queried. Defaults to None.
            inputs (list, optional): List of inputs to be queried. Defaults to None.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, json_data = RequestHandler._metadata(
            method="POST", key=key, model_id=model_id, inputs=inputs, parameters=parameters, options=options
        )
        response = None
        for attempt in range(0, ConnectionManager.MAX_RETRIES_TOKENIZE):
            # NOTE: We don't retry-fail with httpx since that'd not
            # not respect the ratelimiting below (5 requests per second).
            # Instead, we do the ratelimiting here with the help of limiter.
            async with ConnectionManager.async_tokenize_limiter:
                response = await ConnectionManager.async_tokenize_client.post(endpoint, headers=headers, json=json_data)
                if response.status_code in [httpx.codes.SERVICE_UNAVAILABLE, httpx.codes.TOO_MANY_REQUESTS]:
                    await asyncio.sleep(2 ** (attempt + 1))
                else:
                    break
        return response

    @staticmethod
    async def async_get(endpoint: str, key: str, parameters: dict = None):
        """Low level API for async /get request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, _ = RequestHandler._metadata(method="GET", key=key)

        async with httpx.AsyncClient(timeout=ConnectionManager.TIMEOUT) as client:
            response = await client.get(url=endpoint, headers=headers, params=parameters)
        return response

    @staticmethod
    def post(
        endpoint: str,
        key: str,
        model_id: str = None,
        inputs: list = None,
        parameters: dict = None,
        streaming: bool = False,
        options: Options = None,
    ):
        """Low level API for /post request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            model_id (str, optional): The id of the language model to be queried. Defaults to None.
            inputs (list, optional): List of inputs to be queried. Defaults to None.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.
            options (Options, optional): Additional parameters to pass in the query payload. Defaults to None.

        Returns:
            httpx.Response: Response from the REST API.
            or
            Generator of streamed response payloads from the REST API.
        """
        headers, json_data = RequestHandler._metadata(
            method="POST", key=key, model_id=model_id, inputs=inputs, parameters=parameters, options=options
        )

        if streaming:
            return RequestHandler.post_stream(endpoint=endpoint, headers=headers, json_data=json_data)
        else:
            with httpx.Client(timeout=ConnectionManager.TIMEOUT) as s:
                response = s.post(url=endpoint, headers=headers, json=json_data)
                return response

    @staticmethod
    def patch(endpoint: str, key: str, json_data: dict = None) -> Response:
        """Low level API for /patch request to REST API.

        Currently only used for TOU endpoint.

        Args:
            endpoint (str):
            key (str)
            payload: (dict, optional)

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, json_data = RequestHandler._metadata(method="PATCH", key=key)

        with httpx.Client(timeout=ConnectionManager.TIMEOUT) as s:
            response = s.patch(url=endpoint, headers=headers, json=json_data)
            return response

    @staticmethod
    def post_stream(endpoint, headers, json_data):
        with httpx.Client(timeout=ConnectionManager.TIMEOUT) as s:
            with s.stream(method="POST", url=endpoint, headers=headers, json=json_data) as r:
                for chunk in r.iter_text():
                    yield chunk

    @staticmethod
    def get(endpoint: str, key: str, parameters: dict = None) -> Response:
        """Low level API for /get request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.

        Returns:
            httpx.Response: Response from the REST API.
        """
        headers, _ = RequestHandler._metadata(method="GET", key=key)
        with httpx.Client(timeout=ConnectionManager.TIMEOUT) as s:
            response = s.get(url=endpoint, headers=headers, params=parameters)
            return response

    @staticmethod
    def put(endpoint: str, key: str, options: Options = None) -> Response:
        """Low level API for /get request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            options (Options, optional): Additional parameters to pass in the query payload. Defaults to None.

        Returns:
            requests.models.Response: Response from the REST API.
        """
        headers, json_data = RequestHandler._metadata(method="PUT", key=key, options=options)
        with httpx.Client(timeout=ConnectionManager.TIMEOUT) as s:
            response = s.put(url=endpoint, headers=headers, json=json_data)
            return response

    @staticmethod
    def delete(endpoint: str, key: str, parameters: dict = None) -> Response:
        """Low level API for /get request to REST API.

        Args:
            endpoint (str): Remote endpoint to be queried.
            key (str): API key for authorization.
            parameters (dict, optional): Key-value pairs for model parameters. Defaults to None.

        Returns:
            requests.models.Response: Response from the REST API.
        """
        headers, _ = RequestHandler._metadata(method="DELETE", key=key)
        with httpx.Client(timeout=ConnectionManager.TIMEOUT) as s:
            response = s.delete(url=endpoint, headers=headers, params=parameters)
            return response
