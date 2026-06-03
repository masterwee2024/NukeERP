interface PanelDef {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface FormPageLayoutProps {
  leftPanel: PanelDef;
  rightPanel: PanelDef;
}

export default function FormPageLayout({ leftPanel, rightPanel }: FormPageLayoutProps) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 h-full">
      <div className="overflow-auto">{leftPanel.content}</div>
      <div className="overflow-auto hidden xl:block">{rightPanel.content}</div>
    </div>
  );
}
