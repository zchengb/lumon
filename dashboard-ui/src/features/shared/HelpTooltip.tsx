import { CircleHelp } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../../shared/i18n";

interface HelpTooltipProps {
  helpId: string;
  label: string;
  help: string;
}

export function FieldLabelWithHelp({ htmlFor, ...props }: HelpTooltipProps & { htmlFor: string }): React.JSX.Element {
  return <div className="field-label-help">
    <div className="field-label-heading">
      <label className="field-label" htmlFor={htmlFor}>{props.label}</label>
      <HelpTooltip {...props} />
    </div>
  </div>;
}

export function HelpTooltip({ helpId, label, help }: HelpTooltipProps): React.JSX.Element {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLParagraphElement>(null);

  useLayoutEffect(() => {
    if (!expanded) return;
    const trigger = triggerRef.current!;
    const tooltip = tooltipRef.current!;
    const anchor = trigger.getBoundingClientRect();
    const bubble = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.max(12, Math.min(anchor.left, window.innerWidth - bubble.width - 12))}px`;
    const below = anchor.bottom + 8;
    const top = below + bubble.height <= window.innerHeight - 12 ? below : anchor.top - bubble.height - 8;
    tooltip.style.top = `${Math.max(12, top)}px`;

    function dismissOutside(event: Event): void {
      if (event.target instanceof Node && !trigger.contains(event.target) && !tooltip.contains(event.target)) {
        setExpanded(false);
      }
    }
    function dismissOnEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        setExpanded(false);
      }
    }
    function dismiss(): void { setExpanded(false); }
    function dismissOnScroll(event: Event): void {
      if (!(event.target instanceof Node) || !tooltip.contains(event.target)) dismiss();
    }
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("focusin", dismissOutside);
    document.addEventListener("keydown", dismissOnEscape);
    window.addEventListener("resize", dismiss);
    document.addEventListener("scroll", dismissOnScroll, true);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("focusin", dismissOutside);
      document.removeEventListener("keydown", dismissOnEscape);
      window.removeEventListener("resize", dismiss);
      document.removeEventListener("scroll", dismissOnScroll, true);
    };
  }, [expanded, help]);

  return <>
    <button ref={triggerRef} className="field-help-toggle" type="button"
      aria-label={`${label} — ${t("settings.fieldHelp")}`}
      aria-expanded={expanded} aria-controls={helpId} aria-describedby={helpId}
      onClick={() => setExpanded(!expanded)}>
      <CircleHelp size={15} aria-hidden="true" />
    </button>
    {createPortal(<p ref={tooltipRef} className="field-help-tooltip" id={helpId} role="tooltip" hidden={!expanded}>{help}</p>, document.body)}
  </>;
}
