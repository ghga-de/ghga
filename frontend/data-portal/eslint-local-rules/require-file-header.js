/**
 * ESLint rule enforcing the required GHGA file header block.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

// The fixed lines of the header (as they appear inside the block comment,
// i.e. between the opening "/*" and closing "*/").
const COPYRIGHT_LINE = ' * @copyright The GHGA Authors';
const LICENSE_LINE = ' * @license Apache-2.0';
// The first line is a free-text module description.
const DESCRIPTION_PATTERN = /^ \* .+$/;
const DESCRIPTION_TEMPLATE = ' * Short module description';

/**
 * Build the full header comment text for a given description line.
 * @param {string} [description] the description line (defaults to a placeholder)
 * @returns {string} the complete block comment, from "/**" to "*\/"
 */
const buildHeader = (description) =>
  [
    '/**',
    description ?? DESCRIPTION_TEMPLATE,
    COPYRIGHT_LINE,
    LICENSE_LINE,
    ' */',
  ].join('\n');

export default {
  meta: {
    type: 'problem',
    fixable: 'code',
    schema: [],
    messages: {
      missing: 'Missing required file header.',
      malformed:
        'Malformed file header: expected a description line followed by @copyright and @license.',
    },
  },

  create(context) {
    const sourceCode = context.sourceCode;
    return {
      Program(node) {
        const first = sourceCode.getAllComments()[0];

        // A valid header is a block comment at the very start of the file.
        if (!first || first.type !== 'Block' || first.range[0] !== 0) {
          context.report({
            node,
            messageId: 'missing',
            fix: (fixer) => fixer.insertTextBeforeRange([0, 0], `${buildHeader()}\n\n`),
          });
          return;
        }

        // The block comment value is the text between "/*" and "*/".
        // For a JSDoc header this splits into:
        //   ['*', ' * <description>', ' * @copyright...', ' * @license...', ' ']
        const lines = first.value.split('\n');
        const description = lines[1];
        const valid =
          lines[0] === '*' &&
          DESCRIPTION_PATTERN.test(description ?? '') &&
          lines[2] === COPYRIGHT_LINE &&
          lines[3] === LICENSE_LINE &&
          lines[4] === ' ';

        if (!valid) {
          // Report on the Program node (first real token) rather than the
          // comment, so a file-level `eslint-disable-next-line` placed before
          // the first statement can suppress a deliberately custom header.
          context.report({
            node,
            messageId: 'malformed',
            fix(fixer) {
              // Preserve an existing valid description; otherwise use the placeholder.
              const keep = DESCRIPTION_PATTERN.test(description ?? '')
                ? description
                : DESCRIPTION_TEMPLATE;
              return fixer.replaceText(first, buildHeader(keep));
            },
          });
        }
      },
    };
  },
};
