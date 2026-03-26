// jsdom doesn't implement HTMLCanvasElement.getContext — LiteGraph needs it at import time
// eslint-disable-next-line immutable/no-mutation
HTMLCanvasElement.prototype.getContext = () => null
