let clientKeySequence = 0;

export type ClientKeyed = {
  _clientKey?: string;
};

export function createClientKey(prefix: string) {
  clientKeySequence += 1;
  return `${prefix}-${clientKeySequence}`;
}

export function withoutClientKey<T extends ClientKeyed>(item: T): T {
  const result = { ...item };
  delete result._clientKey;
  return result;
}
