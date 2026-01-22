#!/usr/bin/env python3
"""
Convert Mist Adoption Set Commands to Configuration Template

This script takes Junos set commands from Mist adoption output and converts them
into a usable configuration format with sensitive information extracted as placeholders.

Usage:
    # Convert from clipboard or file
    ./convert_mist_adoption.py --input mist-adoption.txt --output templates/mist-adopt.template
    
    # Interactive mode
    ./convert_mist_adoption.py --interactive
    
    # From stdin
    cat mist-commands.txt | ./convert_mist_adoption.py --output template.txt
"""

import sys
import argparse
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class MistAdoptionConverter:
    """Converts Mist adoption set commands to configuration templates"""
    
    # Patterns to identify sensitive data that should be templated
    SENSITIVE_PATTERNS = {
        'encrypted_password': (
            r'(set system login user mist authentication encrypted-password\s+)(\S+)',
            '<ENCRYPTED_PASSWORD>'
        ),
        'ssh_key': (
            r'(set system login user mist authentication ssh-rsa\s+)"([^"]+)"',
            '"<SSH_PUBLIC_KEY>"'
        ),
        'device_id': (
            r'(set system services outbound-ssh client mist device-id\s+)(\S+)',
            '<DEVICE_ID>'
        ),
        'secret': (
            r'(set system services outbound-ssh client mist secret\s+)(\S+)',
            '<SECRET>'
        ),
        'mist_hostname': (
            r'(set system services outbound-ssh client mist\s+)(\S+\.mist(?:sys)?\.(?:com|net))',
            '<MIST_HOSTNAME>'
        )
    }
    
    def __init__(self):
        self.extracted_values: Dict[str, str] = {}
    
    def convert_to_template(self, set_commands: str) -> Tuple[str, Dict[str, str]]:
        """
        Convert set commands to template format
        
        Args:
            set_commands: Original Junos set commands from Mist
            
        Returns:
            Tuple of (template_config, extracted_values)
        """
        lines = set_commands.strip().split('\n')
        template_lines = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                template_lines.append(line)
                continue
            
            # Process each sensitive pattern
            processed_line = line
            for pattern_name, (regex, placeholder) in self.SENSITIVE_PATTERNS.items():
                match = re.search(regex, processed_line)
                if match:
                    # Extract the actual value
                    if len(match.groups()) >= 2:
                        actual_value = match.group(2)
                        self.extracted_values[pattern_name] = actual_value
                        # Replace with placeholder
                        processed_line = re.sub(regex, r'\1' + placeholder, processed_line)
            
            template_lines.append(processed_line)
        
        template = '\n'.join(template_lines)
        return template, self.extracted_values
    
    def convert_to_config(self, set_commands: str) -> str:
        """
        Convert set commands to standard configuration format
        (Without placeholders - for direct use)
        
        Args:
            set_commands: Original Junos set commands
            
        Returns:
            Configuration text
        """
        # For now, just clean up and format the set commands
        lines = set_commands.strip().split('\n')
        config_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                config_lines.append(line)
        
        return '\n'.join(config_lines)
    
    def generate_values_file(self, values: Dict[str, str]) -> str:
        """
        Generate a separate file documenting extracted values
        
        Args:
            values: Dictionary of extracted sensitive values
            
        Returns:
            Formatted text with extracted values
        """
        lines = [
            "# Extracted Values from Mist Adoption Commands",
            "# DO NOT COMMIT THIS FILE TO VERSION CONTROL!",
            "#",
            "# Use these values to populate your adoption template",
            "",
        ]
        
        for key, value in values.items():
            lines.append(f"# {key.upper()}:")
            # Truncate very long values for display
            if len(value) > 80:
                display_value = value[:77] + "..."
            else:
                display_value = value
            lines.append(f"# {display_value}")
            lines.append("")
        
        return '\n'.join(lines)


def read_input(input_path: Path = None) -> str:
    """Read input from file or stdin"""
    if input_path:
        with open(input_path, 'r') as f:
            return f.read()
    else:
        # Read from stdin
        return sys.stdin.read()


def interactive_mode() -> str:
    """Interactive mode - paste commands directly"""
    print("\n" + "="*70)
    print("Mist Adoption Command Converter - Interactive Mode")
    print("="*70)
    print("\nPaste your Mist adoption set commands below.")
    print("Press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) when done:\n")
    
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Mist adoption set commands to configuration template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert from file
  ./convert_mist_adoption.py -i mist-commands.txt -o templates/mist-adopt.template
  
  # Interactive mode
  ./convert_mist_adoption.py --interactive
  
  # From stdin
  cat mist-commands.txt | ./convert_mist_adoption.py -o template.txt
  
  # Also extract values to separate file
  ./convert_mist_adoption.py -i input.txt -o template.txt --values values.txt
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=Path,
        help='Input file with Mist set commands (default: stdin)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output template file (default: stdout)'
    )
    parser.add_argument(
        '--values',
        type=Path,
        help='Output file for extracted values (optional)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode - paste commands directly'
    )
    parser.add_argument(
        '--no-template',
        action='store_true',
        help='Output as-is without creating placeholders'
    )
    
    args = parser.parse_args()
    
    # Get input
    if args.interactive:
        set_commands = interactive_mode()
    else:
        try:
            set_commands = read_input(args.input)
        except FileNotFoundError:
            logger.error(f"Input file not found: {args.input}")
            return 1
        except Exception as e:
            logger.error(f"Error reading input: {e}")
            return 1
    
    if not set_commands.strip():
        logger.error("No input provided")
        return 1
    
    # Convert
    converter = MistAdoptionConverter()
    
    if args.no_template:
        output = converter.convert_to_config(set_commands)
        logger.info("Converted to configuration format (no placeholders)")
    else:
        output, extracted = converter.convert_to_template(set_commands)
        logger.info(f"Converted to template format ({len(extracted)} sensitive values extracted)")
        
        # Save extracted values if requested
        if args.values:
            values_content = converter.generate_values_file(extracted)
            try:
                args.values.write_text(values_content)
                logger.info(f"Extracted values saved to: {args.values}")
                logger.warning(f"SECURITY: Do not commit {args.values} to version control!")
            except Exception as e:
                logger.error(f"Error writing values file: {e}")
    
    # Output
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output)
            logger.info(f"Template saved to: {args.output}")
            if not args.no_template:
                logger.warning(f"REMINDER: Add {args.output} to .gitignore if it contains real values")
        except Exception as e:
            logger.error(f"Error writing output file: {e}")
            return 1
    else:
        print("\n" + "="*70)
        print("GENERATED TEMPLATE:")
        print("="*70)
        print(output)
        print("="*70)
    
    # Helpful reminders
    if not args.no_template:
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Review the generated template file")
        print("2. Add template file to .gitignore if it contains real values")
        print("3. Use template with: ./fabriclab.py create --adopt-template <file>")
        print("="*70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
