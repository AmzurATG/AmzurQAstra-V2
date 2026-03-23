import { Router, Request, Response, NextFunction } from 'express'
import { BrowserManager } from '../core/browserManager'
import { executeAction, executeActions, ActionInput } from '../core/actionExecutor'
import { logger } from '../utils/logger'

export function createMcpRoutes(browserManager: BrowserManager): Router {
  const router = Router()

  // Execute a single action
  router.post('/execute', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { sessionId, action } = req.body as { sessionId: string; action: ActionInput }

      if (!sessionId || !action) {
        return res.status(400).json({ error: 'sessionId and action are required' })
      }

      const session = browserManager.getSession(sessionId)
      if (!session) {
        return res.status(404).json({ error: `Session not found: ${sessionId}` })
      }

      browserManager.updateActivity(sessionId)
      const result = await executeAction(session.page, action)

      res.json(result)
    } catch (error) {
      next(error)
    }
  })

  // Execute multiple actions (test case)
  router.post('/execute-batch', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { sessionId, actions } = req.body as { sessionId: string; actions: ActionInput[] }

      if (!sessionId || !actions || !Array.isArray(actions)) {
        return res.status(400).json({ error: 'sessionId and actions array are required' })
      }

      const session = browserManager.getSession(sessionId)
      if (!session) {
        return res.status(404).json({ error: `Session not found: ${sessionId}` })
      }

      browserManager.updateActivity(sessionId)
      const results = await executeActions(session.page, actions)

      const allPassed = results.every((r) => r.success)
      res.json({
        success: allPassed,
        totalActions: actions.length,
        executedActions: results.length,
        results,
      })
    } catch (error) {
      next(error)
    }
  })

  // Capture screenshot
  router.post('/screenshot', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { sessionId, fullPage = false } = req.body as { sessionId: string; fullPage?: boolean }

      if (!sessionId) {
        return res.status(400).json({ error: 'sessionId is required' })
      }

      const session = browserManager.getSession(sessionId)
      if (!session) {
        return res.status(404).json({ error: `Session not found: ${sessionId}` })
      }

      browserManager.updateActivity(sessionId)
      
      const screenshot = await session.page.screenshot({
        fullPage,
        type: 'png',
      })

      res.json({
        success: true,
        screenshot: screenshot.toString('base64'),
        url: session.page.url(),
        timestamp: new Date().toISOString(),
      })
    } catch (error) {
      next(error)
    }
  })

  // Get page info
  router.get('/page-info/:sessionId', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { sessionId } = req.params

      const session = browserManager.getSession(sessionId)
      if (!session) {
        return res.status(404).json({ error: `Session not found: ${sessionId}` })
      }

      browserManager.updateActivity(sessionId)

      const url = session.page.url()
      const title = await session.page.title()

      res.json({
        sessionId,
        url,
        title,
        browserType: session.browserType,
        lastActivity: session.lastActivity,
      })
    } catch (error) {
      next(error)
    }
  })

  return router
}
