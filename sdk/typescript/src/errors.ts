export class OpenQueueError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "OpenQueueError";
  }
}

export class AuthenticationError extends OpenQueueError {
  constructor(message: string = "Invalid API token") {
    super(message);
    this.name = "AuthenticationError";
  }
}

export class JobNotFoundError extends OpenQueueError {
  constructor(message: string = "Job not found") {
    super(message);
    this.name = "JobNotFoundError";
  }
}

export class LeaseTokenError extends OpenQueueError {
  constructor(message: string = "Lease token mismatch or job not in processing state") {
    super(message);
    this.name = "LeaseTokenError";
  }
}

export class ValidationError extends OpenQueueError {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

export class RateLimitError extends OpenQueueError {
  constructor(message: string = "Rate limit exceeded") {
    super(message);
    this.name = "RateLimitError";
  }
}
