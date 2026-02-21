"""
Run all pipeline steps: analyze -> export CSV -> visualize

Convenience script that runs the full pipeline in sequence,
passing through common arguments like --filter and --verbose.
"""

import argparse
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        description='Run full analysis pipeline (analyze + export + visualize)')
    parser.add_argument('--filter', default='all',
                        help='Elo filter to process (default: all)')
    parser.add_argument('--patches', choices=['current', 'last3'], default='last3',
                        help='Patch range to include (default: last3)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    src_dir = os.path.dirname(os.path.abspath(__file__))
    common_args = []
    if args.filter != 'all':
        common_args += ['--filter', args.filter]
    if args.verbose:
        common_args.append('--verbose')

    steps = [
        ('Analyze', [sys.executable, os.path.join(src_dir, 'analyze.py'),
                      '--patches', args.patches] + common_args),
        ('Export CSV', [sys.executable, os.path.join(src_dir, 'export_csv.py')] + common_args),
        ('Visualize', [sys.executable, os.path.join(src_dir, 'visualize.py')] + common_args),
    ]

    for step_name, cmd in steps:
        print(f"\n{'='*60}")
        print(f"  {step_name}")
        print(f"{'='*60}\n")

        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\n{step_name} failed with exit code {result.returncode}")
            sys.exit(result.returncode)

    print(f"\n{'='*60}")
    print("  Pipeline complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
