import type { TestStep, TestStepAction } from '../types'

const ACTIONS_REQUIRING_TARGET: TestStepAction[] = [
  'navigate',
  'click',
  'fill',
  'type',
  'select',
  'check',
  'uncheck',
  'hover',
  'assert_visible',
  'assert_text',
  'assert_title',
]

const ACTIONS_REQUIRING_VALUE: TestStepAction[] = [
  'fill',
  'type',
  'select',
  'assert_url',
  'assert_text',
]

export function validateTestStepFields(step: Pick<TestStep, 'action' | 'description' | 'target' | 'value'>): string[] {
  const errors: string[] = []
  const desc = (step.description || '').trim()
  const tgt = (step.target || '').trim()
  const val = (step.value || '').trim()

  if (!desc) {
    errors.push('Description is required')
  }
  if (ACTIONS_REQUIRING_TARGET.includes(step.action) && !tgt) {
    errors.push(`Target is required for action "${step.action}"`)
  }
  if (ACTIONS_REQUIRING_VALUE.includes(step.action) && !val) {
    errors.push(`Value is required for action "${step.action}"`)
  }

  return errors
}
