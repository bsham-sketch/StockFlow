export function formatPrice(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
  }).format(value);
}

export function formatProductName(value) {
  return value.replace(/\b\w/g, (character) => character.toUpperCase());
}
