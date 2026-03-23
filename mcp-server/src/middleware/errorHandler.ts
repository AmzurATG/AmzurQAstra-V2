import { Request, Response, NextFunction } from 'express'
import { logger } from '../utils/logger'

export function errorHandler(
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  logger.error('Request error:', {
    method: req.method,
    path: req.path,
    error: error.message,
    stack: error.stack,
  })

  res.status(500).json({
    error: 'Internal server error',
    message: error.message,
  })
}
