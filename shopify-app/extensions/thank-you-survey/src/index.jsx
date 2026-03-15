import { Text, extension } from "@shopify/ui-extensions/checkout";

export default extension("purchase.thank-you.block.render", (root) => {
  root.appendChild(
    root.createComponent(
      Text,
      {},
      "Thank-you survey extension is active.",
    ),
  );
});
