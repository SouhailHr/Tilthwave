import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WaterConsumptionChart } from "./water-consumption-chart-impl";

describe("WaterConsumptionChart", () => {
  it("totals only the months that have happened and labels the year", () => {
    const data = { August: { Total: 1000 }, September: { Total: 612000 }, December: { Total: 99 } };
    render(<WaterConsumptionChart data={data as never} now={new Date(2026, 8, 23)} />);
    // December has not happened in September: its (stray) value is not counted.
    expect(screen.getByText(/613,000 m³/)).toBeInTheDocument();
    expect(screen.getByText("Monthly total, m³")).toBeInTheDocument();
  });

  it("says so when there is no data", () => {
    render(<WaterConsumptionChart data={undefined} />);
    expect(screen.getByText("No data.")).toBeInTheDocument();
  });
});
