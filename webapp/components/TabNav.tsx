"use client";

import * as Tabs from "@radix-ui/react-tabs";

const TABS = [
  { value: "s1", label: "Visão geral" },
  { value: "s2", label: "Previsão de volume" },
  { value: "s3", label: "Risco e explicabilidade" },
  { value: "s4", label: "Tendências e insights" },
  { value: "s5", label: "Resultados dos modelos" },
];

export default function TabNav() {
  return (
    <Tabs.List className="sticky top-[53px] z-[55] flex gap-0.5 overflow-x-auto border-b border-line bg-bg px-6 pt-2.5">
      {TABS.map((tab) => (
        <Tabs.Trigger
          key={tab.value}
          value={tab.value}
          className="whitespace-nowrap border-b-2 border-transparent px-4 pb-3 pt-2.5 font-inter text-[0.84rem] font-semibold text-mut transition-colors hover:text-txt data-[state=active]:border-red data-[state=active]:text-txt"
        >
          {tab.label}
        </Tabs.Trigger>
      ))}
    </Tabs.List>
  );
}
