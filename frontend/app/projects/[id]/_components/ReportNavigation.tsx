"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  useForgeLanguage,
} from "@/lib/language-context";


type NavigationLanguage =
  | "fr"
  | "en";


type NavItem = {
  id: string;
  label: string;
  group:
    | "report"
    | "product";
  depth?: 0 | 1;
};


const navItems: Record<
  NavigationLanguage,
  NavItem[]
> = {
  fr: [
    { id: "executive-summary", label: "R\u00e9sum\u00e9", group: "report" },
    { id: "problem", label: "Probl\u00e8me", group: "report" },
    { id: "solution", label: "Solution", group: "report" },
    { id: "target-market", label: "March\u00e9", group: "report" },
    { id: "personas", label: "Personas", group: "report" },
    { id: "market-opportunity", label: "Opportunit\u00e9", group: "report" },
    { id: "swot", label: "SWOT", group: "report" },
    { id: "bmc", label: "Business Model", group: "report" },
    { id: "sources", label: "Sources", group: "report" },
    { id: "financial", label: "Finance", group: "report" },
    { id: "startup-score", label: "Score", group: "report" },
    { id: "debate", label: "D\u00e9bat IA", group: "report" },
    { id: "verdict", label: "Verdict", group: "report" },
    { id: "action-plan", label: "Plan d\u2019actions", group: "report" },
    { id: "limitations", label: "Limites", group: "report" },

    { id: "project-manager", label: "Plan produit", group: "product" },
    { id: "product-plan-overview", label: "Vue d\u2019ensemble", group: "product", depth: 1 },
    { id: "product-plan-settings", label: "R\u00e9glages", group: "product", depth: 1 },
    { id: "product-plan-backlog", label: "Backlog", group: "product", depth: 1 },
    { id: "product-plan-sprints", label: "Sprints", group: "product", depth: 1 },
    { id: "product-plan-dependencies", label: "D\u00e9pendances", group: "product", depth: 1 },
    { id: "product-plan-metrics", label: "M\u00e9triques", group: "product", depth: 1 },
    { id: "product-plan-advice", label: "Conseils Scrum", group: "product", depth: 1 },
  ],

  en: [
    { id: "executive-summary", label: "Summary", group: "report" },
    { id: "problem", label: "Problem", group: "report" },
    { id: "solution", label: "Solution", group: "report" },
    { id: "target-market", label: "Market", group: "report" },
    { id: "personas", label: "Personas", group: "report" },
    { id: "market-opportunity", label: "Opportunity", group: "report" },
    { id: "swot", label: "SWOT", group: "report" },
    { id: "bmc", label: "Business Model", group: "report" },
    { id: "sources", label: "Sources", group: "report" },
    { id: "financial", label: "Finance", group: "report" },
    { id: "startup-score", label: "Score", group: "report" },
    { id: "debate", label: "AI Debate", group: "report" },
    { id: "verdict", label: "Verdict", group: "report" },
    { id: "action-plan", label: "Action plan", group: "report" },
    { id: "limitations", label: "Limits", group: "report" },

    { id: "project-manager", label: "Product plan", group: "product" },
    { id: "product-plan-overview", label: "Overview", group: "product", depth: 1 },
    { id: "product-plan-settings", label: "Settings", group: "product", depth: 1 },
    { id: "product-plan-backlog", label: "Backlog", group: "product", depth: 1 },
    { id: "product-plan-sprints", label: "Sprints", group: "product", depth: 1 },
    { id: "product-plan-dependencies", label: "Dependencies", group: "product", depth: 1 },
    { id: "product-plan-metrics", label: "Metrics", group: "product", depth: 1 },
    { id: "product-plan-advice", label: "Scrum advice", group: "product", depth: 1 },
  ],
};


function sameItems(
  left: NavItem[],
  right: NavItem[],
) {
  return (
    left.length === right.length
    &&
    left.every(
      (
        item,
        index,
      ) =>
        item.id === right[index]?.id
        &&
        item.label === right[index]?.label
        &&
        item.group === right[index]?.group
        &&
        item.depth === right[index]?.depth,
    )
  );
}


export default function ReportNavigation() {
  const {
    lang,
  } = useForgeLanguage();


  const language:
    NavigationLanguage =
      lang === "en"
        ? "en"
        : "fr";


  const candidates =
    navItems[
      language
    ];


  const [
    items,
    setItems,
  ] = useState<
    NavItem[]
  >([]);


  const [
    activeId,
    setActiveId,
  ] = useState("");


  useEffect(
    () => {
      let frame = 0;


      const refreshItems = () => {
        window.cancelAnimationFrame(
          frame,
        );

        frame =
          window.requestAnimationFrame(
            () => {
              const next =
                candidates.filter(
                  (item) =>
                    document.getElementById(
                      item.id,
                    )
                    !==
                    null,
                );


              setItems(
                (current) =>
                  sameItems(
                    current,
                    next,
                  )
                    ? current
                    : next,
              );


              setActiveId(
                (current) =>
                  (
                    current
                    &&
                    next.some(
                      (item) =>
                        item.id === current,
                    )
                  )
                    ? current
                    : (
                        next[0]?.id
                        ??
                        ""
                      ),
              );
            },
          );
      };


      refreshItems();


      const mutationObserver =
        new MutationObserver(
          refreshItems,
        );


      mutationObserver.observe(
        document.body,
        {
          childList: true,
          subtree: true,
        },
      );


      return () => {
        mutationObserver.disconnect();

        window.cancelAnimationFrame(
          frame,
        );
      };
    },
    [
      candidates,
    ],
  );


  useEffect(
    () => {
      const elements =
        items
          .map(
            (item) =>
              document.getElementById(
                item.id,
              ),
          )
          .filter(
            (
              element,
            ): element is HTMLElement =>
              element !== null,
          );


      if (
        elements.length
        ===
        0
      ) {
        return;
      }


      const observer =
        new IntersectionObserver(
          (entries) => {
            const visible =
              entries
                .filter(
                  (entry) =>
                    entry.isIntersecting,
                )
                .sort(
                  (
                    left,
                    right,
                  ) =>
                    right.intersectionRatio
                    -
                    left.intersectionRatio,
                );


            const current =
              visible[0];


            if (current) {
              setActiveId(
                current.target.id,
              );
            }
          },
          {
            rootMargin:
              "-18% 0px -68% 0px",

            threshold: [
              0,
              0.1,
              0.35,
              0.6,
            ],
          },
        );


      elements.forEach(
        (element) =>
          observer.observe(
            element,
          ),
      );


      return () => {
        observer.disconnect();
      };
    },
    [
      items,
    ],
  );


  const reportItems =
    items.filter(
      (item) =>
        item.group
        ===
        "report",
    );


  const productItems =
    items.filter(
      (item) =>
        item.group
        ===
        "product",
    );


  const renderLink = (
    item: NavItem,
    compact = false,
  ) => {
    const active =
      activeId
      ===
      item.id;


    return (
      <a
        key={item.id}
        href={`#${item.id}`}
        aria-current={
          active
            ? "location"
            : undefined
        }
        className={[
          "block rounded-xl transition",
          compact
            ? "px-3 py-2 text-sm"
            : "px-3 py-2 text-xs",
          item.depth === 1
            ? "ml-3"
            : "",
          active
            ? "bg-violet-100 font-black text-violet-800"
            : "font-bold text-slate-600 hover:bg-slate-100 hover:text-slate-950",
        ].join(
          " ",
        )}
      >
        {item.label}
      </a>
    );
  };


  if (
    items.length
    ===
    0
  ) {
    return null;
  }


  return (
    <>
      <details className="rounded-2xl border border-slate-200 bg-white shadow-sm lg:hidden">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-black text-slate-800">
          {
            language === "en"
              ? "Report contents"
              : "Sommaire du rapport"
          }
        </summary>

        <nav
          className="max-h-[60vh] space-y-1 overflow-y-auto border-t border-slate-100 p-3"
          aria-label={
            language === "en"
              ? "Report contents"
              : "Sommaire du rapport"
          }
        >
          {
            reportItems.map(
              (item) =>
                renderLink(
                  item,
                  true,
                ),
            )
          }

          {
            productItems.length > 0
            &&
            (
              <>
                <div className="my-2 border-t border-slate-200" />

                {
                  productItems.map(
                    (item) =>
                      renderLink(
                        item,
                        true,
                      ),
                  )
                }
              </>
            )
          }
        </nav>
      </details>


      <aside className="hidden lg:sticky lg:top-24 lg:block lg:self-start">
        <div className="max-h-[calc(100vh-7rem)] overflow-y-auto rounded-3xl border border-slate-200 bg-white/90 p-4 shadow-lg shadow-slate-200/60 backdrop-blur">
          <p className="px-3 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">
            {
              language === "en"
                ? "Report"
                : "Rapport"
            }
          </p>

          <nav
            className="mt-3 space-y-1"
            aria-label={
              language === "en"
                ? "Report contents"
                : "Sommaire du rapport"
            }
          >
            {
              reportItems.map(
                (item) =>
                  renderLink(
                    item,
                  ),
              )
            }

            {
              productItems.length > 0
              &&
              (
                <>
                  <div className="my-3 border-t border-slate-200" />

                  <p className="px-3 pb-1 text-[11px] font-black uppercase tracking-[0.16em] text-violet-500">
                    {
                      language === "en"
                        ? "Product plan"
                        : "Plan produit"
                    }
                  </p>

                  {
                    productItems.map(
                      (item) =>
                        renderLink(
                          item,
                        ),
                    )
                  }
                </>
              )
            }
          </nav>
        </div>
      </aside>
    </>
  );
}
