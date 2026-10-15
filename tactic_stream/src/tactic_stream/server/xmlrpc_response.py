"""Lossless integer response tags understood by the native XML-RPC clients."""
from xmlrpc.client import Marshaller


class ResponseMarshaller(Marshaller):
    dispatch = Marshaller.dispatch.copy()

    def dump_integer(self, value, write):
        if -(2**31) <= value < 2**31:
            tag = 'int'
        elif -(2**63) <= value < 2**63:
            tag = 'i8'
        else:
            tag = 'biginteger'
        write(f'<value><{tag}>{value}</{tag}></value>\n')

    dispatch[int] = dump_integer


def encode_response(value) -> bytes:
    body = ResponseMarshaller('utf-8', allow_none=True).dumps((value,))
    return ("<?xml version='1.0'?>\n<methodResponse>\n" + body + '</methodResponse>\n').encode('utf-8')
