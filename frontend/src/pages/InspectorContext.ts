import { createContext, useContext } from 'react';
import type { ChosenDistribution } from './TransitionInspector';

export interface InspectorRequest {
  edgeId: string;
  fromLabel: string;
  toLabel: string;
  sojournTimes: number[];
  initial: ChosenDistribution | null;
  probability: number;
}

export const InspectorContext = createContext<(req: InspectorRequest) => void>(() => {});
export const useOpenInspector = () => useContext(InspectorContext);
