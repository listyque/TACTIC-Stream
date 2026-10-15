

from __future__ import print_function

__all__ = ['TacticPasswordHasher']

import hashlib

# Copied from: https://djangosnippets.org/snippets/2729/#c4520


"""Original TACTIC $S$ password encoding, retained for existing account hashes.

Algorithm adopted from pyasm/security/drupal_password_hasher.py.
See LICENSE.TACTIC and compatibility/source_manifest.json.
"""

import hashlib, sys

_ITOA64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

IS_Pv3 = sys.version_info[0] > 2


class TacticPasswordHasher(object):
    algorithm = u'S'
    iter_code = u'C'
    salt_length = 8

    def encode(self, password, salt, iter_code=None):
        """Encode the original TACTIC salted SHA-512 password format"""
        
        try:
            b_password = password.encode("utf8")
        except Exception as e:
            b_password = password

        try:
            b_salt = salt.encode("utf8")
        except Exception as e:
            b_salt = salt


        if iter_code == None:
            iterations = 2 ** _ITOA64.index(self.iter_code)
        else:
            iterations = 2 ** _ITOA64.index(iter_code)
        hash = hashlib.sha512(b_salt + b_password).digest()

        for i in range(iterations):
            hash = hashlib.sha512(hash + b_password).digest()

        l = len(hash)

        output = ''
        i = 0

        while i < l:

            if IS_Pv3:
                value = hash[i] # python 3
            else:
                value = ord(hash[i])

            i = i + 1

            output += _ITOA64[value & 0x3f]
            if i < l:
                if IS_Pv3:
                    num = hash[i] # python 3
                else:
                    num = ord(hash[i])
                value |= num << 8

            output += _ITOA64[(value >> 6) & 0x3f]
            if i >= l:
                break
            i += 1

            if i < l:
                if IS_Pv3:
                    num = hash[i] # python 3
                else:
                    num = ord(hash[i])
                value |= num << 16

            output += _ITOA64[(value >> 12) & 0x3f]
            if i >= l:
                break
            i += 1

            output += _ITOA64[(value >> 18) & 0x3f]


        longhashed = "%s$%s%s%s" % (self.algorithm, iter_code,
                                    salt, output)
        return "$%s" % longhashed[:54]

    def verify(self, password, encoded):
        hash = encoded.split("$S$")[1]
        iter_code = hash[0]
        salt = hash[1:1 + self.salt_length]
        tt = self.encode(password, salt, iter_code)

        return encoded == self.encode(password, salt, iter_code)







