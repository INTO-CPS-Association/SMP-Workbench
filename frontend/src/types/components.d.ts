// src/types/components.d.ts
declare module './components/Button' {
  import { FC } from 'react';

  const Button: FC<{}>; // no props
  export default Button;
}