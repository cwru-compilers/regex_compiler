"""
Compile simple regular expressions to bytecode for hendersonvm.

This module implements a compiler for basic regular expressions. The grammar
implementation is based on the one described in the `1997 Single UNIX
Specification <http://opengroup.org/onlinepubs/007908775/xbd/re.html>`_.

The allowed operators are ?, +, *, (), and escape sequences for those
characters. No other escape sequences are supported.
"""

import json
import logging
import optparse
import os
import subprocess
import sys

import instructions
import lexer
import parser
import visualize
from rajax.const import opcode_to_cmd


log = logging.getLogger(__name__)


def show(s, reduced=True, dot_path=None, pdf_path=None, print_tokens=False,
         fmt='pretty'):
    """Generates a graphviz diagram of the AST for the given path. Since this
    is mostly debug functionality, there are also options to print various
    significant values.

    :param s: The regular expression to parse
    :param reduced: If True, includes only productions used for generating code
                    in the diagram. If False, includes all productions in the
                    diagram. Defaults to True.
    :param out_path: Destination for the graphviz document without any
                     extension
    :param make_pdf: Also create a PDF using the local graphviz installation
    :param print_tokens: Print the tokens as seen by the lexer to the console
    :param json: Print json to the console instead of text
    """
    ALLOWED_FORMATS = ('pretty', 'json')
    if fmt not in ALLOWED_FORMATS:
        raise ValueError('fmt must be one of %r' % ALLOWED_FORMATS)

    log.info('dot path: %s' % dot_path)

    if fmt == 'pretty':
        log.info('Tokens:')
        lexer.lexer.input(s)
        for tok in iter(lexer.lexer.token, None):
            log.info(repr(tok.type), repr(tok.value))
    root = parser.parse(s, (not reduced))

    if pdf_path:
        visualize.ast_dot(root, dot_path)
        log.info("Graphviz written to %s" % dot_path)
        try:
            subprocess.call(["dot", "-Tpdf",  dot_path, "-o",  pdf_path])
            log.info("PDF written to %s" % pdf_path)
        except OSError:
            log.info("PDF could not be written, Graphviz does not appear to be"
                     " installed")

    instr_list = root.generate_instructions()
    instr_list.append(instructions.Instruction('match'))
    # Print instructions after the AST is drawn in case instruction printing
    # fails
    program = instructions.serialize(instr_list)

    if fmt == 'json':
        program = [(opcode_to_cmd[inst[0]].upper(), inst[1], inst[2])
                   for inst in program]
        json.dump(program, sys.stdout)
    elif fmt == 'pretty':
        log.info("Instructions for VM:")
        instructions.prettyprint_program(program)


def parse(s):
    """
    Converts a regular expression into bytecode for the VM

    :param s: A regular expression
    :return: A list of opcode tuples in the form `[(opcode, arg1, arg2)]`
    """
    instr_list = parser.parse(s).generate_instructions()
    instr_list.append(instructions.Instruction('match'))
    return instructions.serialize(instr_list)


def main(args):
    p = optparse.OptionParser('Compile a regular expression into NFA'
                              ' instructions')
    p.add_option('-d', '--dot', help='Write the AST as a Graphviz dot file')
    p.add_option('-f', '--format', default='pretty',
                 help='Output format, either "pretty" or "json"')
    p.add_option('-j', '--json', action='store_true',
                 help='Alias for --format=json')
    p.add_option('-p', '--pdf', help=('Write the AST as a PDF file. Implies'
                                      ' --dot=FILENAME.dot.'))
    p.add_option('-v', '--verbose', action='store_true',
                 help='Print debugging information')

    opts, args = p.parse_args()

    logging.basicConfig(level=logging.INFO if opts.verbose
                        else logging.WARNING)

    if len(args) != 1:
        p.error('You must specify exactly one regular expression.')

    if opts.pdf and not opts.dot:
        dot_path = '%s.dot' % os.path.splitext(opts.pdf)[0]
    else:
        dot_path = opts.dot

    fmt = 'json' if opts.json else opts.format

    show(args[0], fmt=fmt.lower(), pdf_path=opts.pdf, dot_path=dot_path)


if __name__ == "__main__":
    parser.debug = False
    main(sys.argv[1:])
