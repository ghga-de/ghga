export default {
  meta: {
    type: 'problem',
    schema: [],
    messages: {
      tooLong:
        'data-umami-event must be at most 50 characters. Current length: {{length}}.',
    },
  },

  create(context) {
    return {
      'TextAttribute[name="data-umami-event"]'(node) {
        const value = node.value ?? '';

        if (value.length > 50) {
          context.report({
            loc: {
              start: {
                line: node.sourceSpan.start.line + 1,
                column: node.sourceSpan.start.col,
              },
              end: {
                line: node.sourceSpan.end.line + 1,
                column: node.sourceSpan.end.col,
              },
            },
            messageId: 'tooLong',
            data: {
              length: String(value.length),
            },
          });
        }
      },
    };
  },
};
