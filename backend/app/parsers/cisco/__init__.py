"""Expose the Cisco parser from one place."""

from app.parsers.cisco.parser import CiscoParser, CiscoParseResult, parse_cisco

__all__ = ["CiscoParser", "CiscoParseResult", "parse_cisco"]
