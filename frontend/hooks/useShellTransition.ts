"use client";

import { createContext, useContext } from "react";

type TransitionRunner = (callback: () => void) => void;

const ShellTransitionContext = createContext<TransitionRunner>((callback) => {
  callback();
});

export const useShellTransition = () => useContext(ShellTransitionContext);

export const ShellTransitionProvider = ShellTransitionContext.Provider;


