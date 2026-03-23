import { Page } from 'playwright'
import { logger } from '../utils/logger'

export type ActionType =
  | 'navigate'
  | 'click'
  | 'fill'
  | 'select'
  | 'check'
  | 'uncheck'
  | 'hover'
  | 'wait'
  | 'waitForSelector'
  | 'screenshot'
  | 'assertVisible'
  | 'assertText'
  | 'assertUrl'
  | 'assertValue'
  | 'evaluate'

export interface ActionInput {
  action: ActionType
  target?: string
  value?: string
  timeout?: number
  options?: Record<string, any>
}

export interface ActionResult {
  success: boolean
  action: ActionType
  target?: string
  duration: number
  error?: string
  data?: any
}

export async function executeAction(page: Page, input: ActionInput): Promise<ActionResult> {
  const startTime = Date.now()
  const timeout = input.timeout || 10000

  try {
    let data: any

    switch (input.action) {
      case 'navigate':
        await page.goto(input.target!, { timeout, waitUntil: 'domcontentloaded' })
        break

      case 'click':
        await page.click(input.target!, { timeout })
        break

      case 'fill':
        await page.fill(input.target!, input.value || '', { timeout })
        break

      case 'select':
        await page.selectOption(input.target!, input.value || '', { timeout })
        break

      case 'check':
        await page.check(input.target!, { timeout })
        break

      case 'uncheck':
        await page.uncheck(input.target!, { timeout })
        break

      case 'hover':
        await page.hover(input.target!, { timeout })
        break

      case 'wait':
        await page.waitForTimeout(parseInt(input.value || '1000', 10))
        break

      case 'waitForSelector':
        await page.waitForSelector(input.target!, { timeout, state: 'visible' })
        break

      case 'screenshot':
        const screenshotBuffer = await page.screenshot({
          fullPage: input.options?.fullPage || false,
          type: 'png',
        })
        data = { screenshot: screenshotBuffer.toString('base64') }
        break

      case 'assertVisible':
        const isVisible = await page.isVisible(input.target!, { timeout })
        if (!isVisible) {
          throw new Error(`Element not visible: ${input.target}`)
        }
        break

      case 'assertText':
        const text = await page.textContent(input.target!, { timeout })
        if (!text?.includes(input.value || '')) {
          throw new Error(`Expected text "${input.value}" not found in element ${input.target}`)
        }
        break

      case 'assertUrl':
        const currentUrl = page.url()
        if (!currentUrl.includes(input.target || '')) {
          throw new Error(`URL assertion failed. Expected: ${input.target}, Got: ${currentUrl}`)
        }
        break

      case 'assertValue':
        const value = await page.inputValue(input.target!, { timeout })
        if (value !== input.value) {
          throw new Error(`Value assertion failed. Expected: ${input.value}, Got: ${value}`)
        }
        break

      case 'evaluate':
        data = await page.evaluate(input.value!)
        break

      default:
        throw new Error(`Unknown action: ${input.action}`)
    }

    const duration = Date.now() - startTime
    logger.debug(`Action ${input.action} completed in ${duration}ms`)

    return {
      success: true,
      action: input.action,
      target: input.target,
      duration,
      data,
    }
  } catch (error: any) {
    const duration = Date.now() - startTime
    logger.error(`Action ${input.action} failed:`, error.message)

    return {
      success: false,
      action: input.action,
      target: input.target,
      duration,
      error: error.message,
    }
  }
}

export async function executeActions(page: Page, actions: ActionInput[]): Promise<ActionResult[]> {
  const results: ActionResult[] = []

  for (const action of actions) {
    const result = await executeAction(page, action)
    results.push(result)

    // Stop on failure unless it's an assertion
    if (!result.success && !action.action.startsWith('assert')) {
      break
    }
  }

  return results
}
