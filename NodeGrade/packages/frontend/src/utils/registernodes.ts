/**
 * Node registration is handled automatically by @haski/ta-lib.
 *
 * When any symbol is imported from @haski/ta-lib, the library's
 * nodes/index.ts is evaluated, which calls LGraphRegisterCustomNodes()
 * immediately at module load time — registering all 34 custom nodes
 * (LLMNode, QuestionNode, OutputNode, ConceptGradeNode, etc.) before
 * any React component mounts.
 *
 * This file is retained as documentation and as an extension point:
 * if you need to register app-specific nodes that are NOT part of
 * @haski/ta-lib, add them here and call registerAppNodes() from Editor.tsx.
 */
import { LGraphRegisterCustomNodes } from '@haski/ta-lib'

export { LGraphRegisterCustomNodes }
