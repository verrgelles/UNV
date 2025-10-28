from hardware.spincore import impulse_builder

#0 Osc
# 3 Gen

impulse_builder(
    2,
    [0, 3],
    [1,1],
    [0,0],
    [0,5],
    int(100),
    int(1E3),
    int(1E3)
)

print("132")